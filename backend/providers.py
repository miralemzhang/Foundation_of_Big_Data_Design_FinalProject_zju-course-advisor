"""Small adapters for the existing BaiLian knowledge base and Qwen tool calling."""
import os
import requests

class ProviderError(RuntimeError):
    def __init__(self,code,message,status=502):
        self.code,self.status=code,status
        super().__init__(message)

class Cloud:
    def __init__(self):
        self.key=os.getenv('DASHSCOPE_API_KEY','')
        self.workspace=os.getenv('BAILIAN_WORKSPACE_ID','')
        self.index=os.getenv('BAILIAN_KNOWLEDGE_IDS','').split(',')[0]
        self.base=os.getenv('QWEN_BASE_URL',f'https://{self.workspace}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1')
        self.model=os.getenv('QWEN_MODEL','qwen-plus')
        self.http=requests.Session()

    def _call(self,url,body,timeout):
        if not self.key: raise ProviderError('missing_api_key','后端未配置百炼凭证',503)
        try:
            r=self.http.post(url,headers={'Authorization':'Bearer '+self.key},json=body,timeout=(5,max(1,timeout)))
            if r.status_code!=200:
                # Upstream bodies may contain links and internals: expose only the error code.
                try:code=r.json().get('code') or r.json().get('error',{}).get('code')
                except ValueError:code=None
                raise ProviderError(str(code or 'upstream_error'),f'模型／知识库服务失败（HTTP {r.status_code}）')
            return r.json()
        except requests.Timeout as e: raise ProviderError('upstream_timeout','模型／知识检索超时',504) from e
        except requests.RequestException as e: raise ProviderError('upstream_connection','无法连接模型／知识库服务') from e
        except ValueError as e: raise ProviderError('upstream_json','上游返回了无法解析的响应') from e

    def chat(self,messages,tools=None,timeout=40,final=False):
        body={'model':self.model,'messages':messages,'temperature':0,'max_tokens':2200}
        if tools:body['tools']=tools
        if final:body['response_format']={'type':'json_object'}
        result=self._call(self.base.rstrip('/')+'/chat/completions',body,timeout)
        try:message=result['choices'][0]['message']
        except (KeyError,IndexError,TypeError) as e:raise ProviderError('upstream_shape','模型返回缺少消息字段') from e
        return message,result.get('usage'),result.get('model',self.model)

    def retrieve(self,query,timeout=15):
        if not self.workspace or not self.index: raise ProviderError('missing_knowledge_config','未配置知识库',503)
        data=self._call(f'https://{self.workspace}.cn-beijing.maas.aliyuncs.com/api/v1/indices/rag/index/retrieve',
            {'index_id':self.index,'query':query,'top_k':5,'dense_similarity_top_k':5,'rerank_top_n':5},timeout)
        if data.get('success') is False:raise ProviderError(str(data.get('code','rag_error')),'知识库未成功完成检索')
        nodes=data.get('data',{}).get('nodes',[])
        # Deliberately omit signed download URLs and all other uncontrolled metadata.
        return [{'evidence_id':'rag_'+str(n.get('metadata',{}).get('_id',i)),
                 'content':n.get('text') or n.get('metadata',{}).get('content',''),
                 'score':n.get('score'),'source':{'knowledge_id':self.index,
                    'document':n.get('metadata',{}).get('doc_name'),
                    'chunk_id':n.get('metadata',{}).get('_id')},'scope':'legacy_knowledge'}
                for i,n in enumerate(nodes[:5])]
