from typing import Dict, List,Literal,Optional, Tuple
from pydantic import BaseModel,Field, field_validator
from utilities import approximate_value
from connection_services import Services

class RecommendationRelationshipSchema(BaseModel):
    type:Literal["affects","is_affected"]
    gain: float
    gain_unit: Optional[str] = None

class RecommendationEntitySchema(BaseModel):
    unit_of_measurement: Optional[str]=None
    name_id:str
    current_value: Optional[float]=None

class RecommendationTargetEntitySchema(RecommendationEntitySchema):
    target_value: Optional[float] = None

class RecommendationLimitEntitySchema(RecommendationEntitySchema):
    priority: Optional[str]=None
    parameter_source: Optional[str]=None

class RecommendationPairElemSchema(RecommendationEntitySchema):
    slack_weight: Optional[RecommendationEntitySchema] =None
    mv_weight: Optional[RecommendationEntitySchema]=None
    low_limits: Optional[List[RecommendationLimitEntitySchema]]=None
    high_limits: Optional[List[RecommendationLimitEntitySchema]]=None

    @field_validator("low_limits",mode="before")
    @staticmethod
    def validate_low_limits(low_limits:Optional[List[RecommendationLimitEntitySchema]])->Optional[List[RecommendationLimitEntitySchema]]:
        new_low_limits = []
        for limit in low_limits:
            if limit["name_id"] is not None:
                new_low_limits.append(limit)
        if new_low_limits == []:
            return None
        return new_low_limits
        
    @field_validator("high_limits",mode="before")
    @staticmethod
    def validate_high_limits(high_limits:Optional[List[RecommendationLimitEntitySchema]])->Optional[List[RecommendationLimitEntitySchema]]:
        new_high_limits = []
        for limit in high_limits:
            if limit["name_id"] is not None:
                new_high_limits.append(limit)
        if new_high_limits == []:
            return None
        return new_high_limits

class RecommendationCalculationEnginePairSchema(BaseModel):
    "schema of each Pair element, out from the neo4j query"
    "from is folloowed by _ because it's a reserved word"
    relationship: RecommendationRelationshipSchema
    from_: RecommendationPairElemSchema = Field(...,alias="from")
    to_: RecommendationPairElemSchema = Field(...,alias="to")

class RecommendationCalculationEngineSchema(BaseModel):
    "schema of the input to the API call of the recommendation calculation engine"
    pairs: List[RecommendationCalculationEnginePairSchema]
    targets: List[RecommendationTargetEntitySchema]
    label: Literal["recommendations","what_if"]

RECOMMENDATION_TEMPLATE = """
    MATCH (start:tag_id)
    where start.name_id in {name_ids}
    CALL apoc.path.subgraphAll(start, {{
    relationshipFilter: "is_affected",
    labelFilter: "+tag_id",
    uniqueness: "NODE_GLOBAL"
    }}) YIELD nodes
    UNWIND nodes AS n
    MATCH (n)-[r:is_affected]->(m:tag_id)
    WITH DISTINCT n, m, r
    // Un solo c1 per ogni n, preferendo :controller se presente
    CALL {{
    WITH n
    MATCH (n)<-[p1:has_parameter]-(c1:instrumentation)
    WITH collect({{p: p1, c: c1}}) AS candidates
    WITH candidates,
    size(candidates) AS count_all,
    [x IN candidates WHERE x.c:controller] AS controllers
    RETURN CASE
    WHEN count_all > 1 AND size(controllers) > 0 THEN controllers[0]
    ELSE candidates[0]
    END AS c1_info
    }}
    // Un solo c2 per ogni m, preferendo :controller se presente
    CALL {{
    WITH m
    MATCH (m)<-[p2:has_parameter]-(c2:instrumentation)
    WITH collect({{p: p2, c: c2}}) AS candidates
    WITH candidates,
    size(candidates) AS count_all,
    [x IN candidates WHERE x.c:controller] AS controllers
    RETURN CASE
    WHEN count_all > 1 AND size(controllers) > 0 THEN controllers[0]
    ELSE candidates[0]
    END AS c2_info
    }}
    WITH
    n, m, r,
    c1_info.c AS c1,
    c2_info.c AS c2,
    c1_info.p.parameter_role AS n_role,
    c2_info.p.parameter_role AS m_role
    // OPTIONAL MATCH relativi a c1 → n
    OPTIONAL MATCH (c1)-[r_hl_1:has_parameter {{parameter_role:'high_limit_variable', main_parameter_role: n_role}}]->(n_hl)
    OPTIONAL MATCH (c1)-[r_ll_1:has_parameter {{parameter_role:'low_limit_variable', main_parameter_role: n_role}}]->(n_ll)
    OPTIONAL MATCH (c1)-[:has_parameter {{parameter_role:'slack_weight', main_parameter_role: n_role}}]->(n_sw)
    // OPTIONAL MATCH relativi a c2 → m
    OPTIONAL MATCH (c2)-[r_hl_2:has_parameter {{parameter_role:'high_limit_variable', main_parameter_role: m_role}}]->(m_hl)
    OPTIONAL MATCH (c2)-[r_ll_2:has_parameter {{parameter_role:'low_limit_variable', main_parameter_role: m_role}}]->(m_ll)
    OPTIONAL MATCH (c2)-[:has_parameter {{parameter_role:'mv_weight', main_parameter_role: m_role}}]->(m_mv)
    OPTIONAL MATCH (c2)-[:has_parameter {{parameter_role:'slack_weight', main_parameter_role: m_role}}]->(m_sw)
    WITH n, m, r, r.gain AS gain, n_sw, m_mv, m_sw,
    collect(DISTINCT {{
    name_id: n_hl.name_id,
    current_value: n_hl.current_value,
    priority: r_hl_1.parameter_priority,
    parameter_source: r_hl_1.parameter_source,
    unit_of_measurement: n_hl.unit_of_measurement
    }}) AS from_high_limits,
    collect(DISTINCT {{
    name_id: n_ll.name_id,
    current_value: n_ll.current_value,
    priority: r_ll_1.parameter_priority,
    parameter_source: r_ll_1.parameter_source,
    unit_of_measurement: n_ll.unit_of_measurement
    }}) AS from_low_limits,
    collect(DISTINCT {{
    name_id: m_hl.name_id,
    current_value: m_hl.current_value,
    priority: r_hl_2.parameter_priority,
    parameter_source: r_hl_2.parameter_source,
    unit_of_measurement: m_hl.unit_of_measurement
    }}) AS to_high_limits,
    collect(DISTINCT {{
    name_id: m_ll.name_id,
    current_value: m_ll.current_value,
    priority: r_ll_2.parameter_priority,
    parameter_source: r_ll_2.parameter_source,
    unit_of_measurement: m_ll.unit_of_measurement
    }}) AS to_low_limits
    RETURN DISTINCT {{
    from: {{
    name_id: n.name_id,
    current_value: n.current_value,
    high_limits: from_high_limits,
    low_limits: from_low_limits,
    slack_weight: CASE WHEN n_sw IS NOT NULL THEN {{
    name_id: n_sw.name_id,
    current_value: n_sw.current_value,
    unit_of_measurement: n_sw.unit_of_measurement
    }} ELSE NULL END
    }},
    relationship: {{
    type: type(r),
    gain: gain,
    gain_unit: r.gain_unit
    }},
    to: {{
    name_id: m.name_id,
    current_value: m.current_value,
    high_limits: to_high_limits,
    low_limits: to_low_limits,
    mv_weight: CASE WHEN m_mv IS NOT NULL THEN {{
    name_id: m_mv.name_id,
    current_value: m_mv.current_value,
    unit_of_measurement: m_mv.unit_of_measurement
    }} ELSE NULL END,
    slack_weight: CASE WHEN m_sw IS NOT NULL THEN {{
    name_id: m_sw.name_id,
    current_value: m_sw.current_value,
    unit_of_measurement: m_sw.unit_of_measurement
    }} ELSE NULL END
    }}
    }} AS pair
    """

def divide_dependent_independent(input:RecommendationCalculationEngineSchema)->Tuple[List[RecommendationPairElemSchema],List[RecommendationPairElemSchema]]:
    variables_name = []
    for item in input.pairs:
        if item.from_.name_id not in variables_name:
            variables_name.append(item.from_.name_id)
        if item.to_.name_id not in variables_name:
            variables_name.append(item.to_.name_id)
    from_node_name = []
    for item in input.pairs:
        if item.from_.name_id not in from_node_name:  #COLLECT ALL THE TAG ID THAT APPEARS IN FROM DICTIONARY
            from_node_name.append(item.from_.name_id)
    independent_variables_name = []
    for item in variables_name:
        if not item in from_node_name:  #SO, IF IT DOESN'T APPEAR IN THE FROM DICTIONARY, SO IT'S NOT AFFECTED FROM NOTHING
            if not item in independent_variables_name:
                independent_variables_name.append(item)
    independent_variables_data = []
    for item in input.pairs:
        if item.to_.name_id in independent_variables_name:
            if item.to_ not in independent_variables_data:
                independent_variables_data.append(item.to_)
    dependent_variables_name = []
    for item in variables_name:
        if not item in independent_variables_name:
            if not item in dependent_variables_name:
                dependent_variables_name.append(item)
    dependent_variables_data = []
    for item in input.pairs:
        if item.from_.name_id in dependent_variables_name:
            if item.from_ not in dependent_variables_data:
                dependent_variables_data.append(item.from_)

    for elem in dependent_variables_data:
        for name_id in input.targets:
            if name_id == elem.name_id:
                dependent_variables_data.remove(elem)

    return dependent_variables_data, independent_variables_data



def build_execute_recommendation_query(name_ids:List[str])->Tuple[List[RecommendationPairElemSchema],List[RecommendationPairElemSchema]]:
    query = RECOMMENDATION_TEMPLATE.format(name_ids=name_ids)
    # let's execute the query
    ############################################ read_query return a list of dict or []
    res = [pair["pair"] for pair in kg.read_query(query,session)]
    ############################################
    # now we need to build the calc_engine API input schema with neo4j query result
    # the targets unit of measurement is the one provided by the user or the one registered in the tsdb.
    targets = [RecommendationTargetEntitySchema(name_id=name_id) for name_id in name_ids]
    calc_engine_request = RecommendationCalculationEngineSchema(pairs=res,targets=targets,label="recommendations")
    # now we can populate te calc_engine_request with the Timescale values
    # let's search for each name_id contained in calc_engine_request
    ts_name_ids = set(name_ids)
    for pair in calc_engine_request.pairs:
        #from
        ts_name_ids.add(pair.from_.name_id)
        for key in pair.from_.model_fields.keys():
            # cerca ogni valore name_id possibile anche nei campi di tipo RecommendationEntitySchema
            field = getattr(pair.from_,key)
            # if its instance of RecommendationEntitySchema or list of RecommendationEntitySchema, we add the name_id to the set
            if isinstance(field, RecommendationEntitySchema):
                ts_name_ids.add(field.name_id)
            elif isinstance(field,list):
                for elem in field:
                    if isinstance(elem, RecommendationLimitEntitySchema):
                        ts_name_ids.add(elem.name_id)
        #to 
        ts_name_ids.add(pair.to_.name_id)
        for key in pair.to_.model_fields.keys():
            # ccerca ogni valore name_id possibile anche nei campi di tipo RecommendationEntitySchema
            field = getattr(pair.to_,key)
            if isinstance(field, RecommendationEntitySchema):
                ts_name_ids.add(field.name_id)
            elif isinstance(field,list):
                for elem in field:
                    if isinstance(elem, RecommendationLimitEntitySchema):
                        ts_name_ids.add(elem.name_id)
    # now we can complete the calc_engine_request with the Timescale values
    ts_name_ids_str = ",".join(["'"+str(elem)+"'" for elem in ts_name_ids])
    ts_name_ids_str = f"({ts_name_ids_str})"
    ts_query =f"""
    select distinct on(tags.name) tags.name, tags.unit_of_measure, ts.value
    from time_series ts
    inner join tags on ts.tag_id = tags.id
    where tags.name in {ts_name_ids_str}
    order by tags.name, ts.timestamp desc
    """
    ############################################
    res = Services.execute_ts_query(query=ts_query,connection=connection,db_key=db_key)
    ############################################
    # let's build for efficiency a dictionary out of the list of resulting rows
    ts_res = {elem["name"]: {"unit_of_measure":elem["unit_of_measure"],"value":approximate_value(elem["value"],digits=4)} for elem in res}
    # let's check taht each target is present in the ts_res and has a valid value 
    # now we can populate the calc_engine_request with the Timescale values
    # first let's fill the targets
    for target in calc_engine_request.targets:
        target.current_value = ts_res[target.name_id]["value"]
        target.unit_of_measurement = ts_res[target.name_id]["unit_of_measure"]
    # now let's fill the pairs
    for pair in calc_engine_request.pairs:
        #from
        pair.from_.current_value = ts_res[pair.from_.name_id]["value"]
        pair.from_.unit_of_measurement = ts_res[pair.from_.name_id]["unit_of_measure"]
        for key in pair.from_.model_fields.keys():
            field = getattr(pair.from_,key)
            #field is already validated and it can be either a RecommendationEntitySchema or a list of RecommendationEntitySchema
            if isinstance(field, RecommendationEntitySchema):
                field.current_value = ts_res[field.name_id]["value"]
                field.unit_of_measurement = ts_res[field.name_id]["unit_of_measure"]
            elif isinstance(field,list):
                for elem in field:
                    if isinstance(elem, RecommendationLimitEntitySchema):
                        elem.current_value = ts_res[elem.name_id]["value"]
                        elem.unit_of_measurement = ts_res[elem.name_id]["unit_of_measure"]
        #to
        pair.to_.current_value = ts_res[pair.to_.name_id]["value"]
        pair.to_.unit_of_measurement = ts_res[pair.to_.name_id]["unit_of_measure"]
        for key in pair.to_.model_fields.keys():
            field = getattr(pair.to_,key)
            if isinstance(field, RecommendationEntitySchema):
                field.current_value = ts_res[field.name_id]["value"]
                field.unit_of_measurement = ts_res[field.name_id]["unit_of_measure"]
            elif isinstance(field,list):
                for elem in field:
                    if isinstance(elem, RecommendationLimitEntitySchema):
                        elem.current_value = ts_res[elem.name_id]["value"]
                        elem.unit_of_measurement = ts_res[elem.name_id]["unit_of_measure"]
    
    ############################################
    # data to fill each request
    calc_engine_result = divide_dependent_independent(calc_engine_request)
    ############################################
    return calc_engine_result




def finish_calc_engine_request(target_values:Dict[str,float],calc_engine_request:RecommendationCalculationEngineSchema):
    # target value is a dict containg the targets_name_id as key and their inputted targets value as value
    for target in calc_engine_request.targets:
        target.target_value = target_values[target.name_id]
    ############################################
    # return calc_engine_request to the AI engine with a call to CHAT-LESS AI
    ############################################
    pass


