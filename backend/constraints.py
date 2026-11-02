"""Small deterministic handling of explicit reset commands; the LLM handles other language."""
import re

VERB=r'(?<!不要)(?<!无需)(?<!不)(?<!别)(?:取消|去掉|移除|清除|清空)\s*(?:对)?'

def explicit_resets(prompt):
    all_fields=bool(re.search(VERB+r'(?:全部|所有)(?:筛选)?(?:条件|限制)',prompt))
    fields=[]
    if re.search(VERB+r'(?:历史)?(?:GPA(?!来源人数)|绩点|均绩)',prompt,re.I) or re.search(r'(?:GPA|绩点|均绩)\s*(?:不再限制|不做限制|不设限制|不限)',prompt,re.I):
        fields+=['min_gpa','max_gpa']
    if re.search(VERB+r'(?:教师|老师)(?:的)?评分(?!人数|数量)',prompt):
        fields+=['min_teacher_rating','max_teacher_rating']
    if re.search(VERB+r'(?:教师|老师)(?:的)?评分人数',prompt):fields+=['min_teacher_rating_count']
    if re.search(VERB+r'GPA来源人数',prompt,re.I):fields+=['min_students']
    return all_fields,set(fields)
