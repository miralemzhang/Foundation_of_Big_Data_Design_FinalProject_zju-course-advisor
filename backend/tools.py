"""Native function-calling schemas. Only these names may be dispatched."""
FILTER_PROPERTIES={
    'min_gpa':{'type':['number','null']},'max_gpa':{'type':['number','null']},
    'min_teacher_rating':{'type':['number','null']},'max_teacher_rating':{'type':['number','null']},
    'min_teacher_rating_count':{'type':['integer','null']},'min_students':{'type':['integer','null']},
    'college':{'type':['string','null']},'categories':{'type':['array','null'],'items':{'type':'string'}}}

def schema(name,description,properties,required=()):
    return {'type':'function','function':{'name':name,'description':description,
        'parameters':{'type':'object','properties':properties,'required':list(required),'additionalProperties':False}}}

TOOLS=[
 schema('search_courses','查询本地通识课。filters_patch只修改用户本轮明确改变的条件；其余条件自动保留。query省略保留原兴趣，空字符串清空兴趣。',
    {'query':{'type':'string'},'filters_patch':{'type':'object','properties':FILTER_PROPERTIES,'additionalProperties':False},
     'reset_filters':{'type':'boolean'},'semantic':{'type':'boolean'},'limit':{'type':'integer','minimum':1,'maximum':10}}),
 schema('get_course_evidence','查看明确课程记录的历史统计和教师评论，并检索既有ai practice知识库。必须使用查询返回的offering_id。',
    {'offering_id':{'type':'string'},'query':{'type':'string','description':'评价方面关键词，如作业；空字符串查一般评价'},
     'use_knowledge':{'type':'boolean'}},['offering_id']),
 schema('find_similar_courses','找到不同名称的相似通识课，保留本轮会话硬条件；相似度不是质量分。',
    {'offering_id':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':10}},['offering_id']),
 schema('compare_courses','对齐2至3个明确的授课记录，返回数值、评价来源和缺失信息。',
    {'offering_ids':{'type':'array','items':{'type':'string'},'minItems':2,'maxItems':3}},['offering_ids'])]
ALLOWED={t['function']['name']:set(t['function']['parameters']['properties']) for t in TOOLS}
