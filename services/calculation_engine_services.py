from schemas.schema import RecommendationCalculationEngineSchema, RecommendationPairElemSchema, RecommendationTargetEntitySchema, RecommendationEntitySchema, RecommendationLimitEntitySchema, RecommendationCalculationEnginePairSchema
from typing import List, Tuple, Dict
from queries.calculation_engine_queries import RECOMMENDATION_TEMPLATE
from utils.log import setup_logger
from services.query_service import KnowledgeGraph, QueryService
from database import get_plant_db
from pydantic import TypeAdapter

logger = setup_logger(__name__)

def divide_dependent_independent(input:RecommendationCalculationEngineSchema)->Tuple[List[RecommendationTargetEntitySchema],List[RecommendationPairElemSchema],List[RecommendationPairElemSchema]]:
    print(f"🔍 divide_dependent_independent called with:")
    print(f"   - pairs count: {len(input.pairs) if input.pairs else 0}")
    print(f"   - targets count: {len(input.targets) if input.targets else 0}")
    
    if not input.pairs:
        print("⚠️ No pairs found, returning empty results")
        return input.targets, [], []
    
    variables_name = []
    from_node_name = []
    independent_variables_name = []
    targets_name_ids = [target.name_id for target in input.targets]
    for item in input.pairs:
        if item.from_.name_id not in variables_name:
            variables_name.append(item.from_.name_id)
        if item.to_.name_id not in variables_name:
            variables_name.append(item.to_.name_id)
        if item.from_.name_id not in from_node_name:
            from_node_name.append(item.from_.name_id)
    for item in variables_name:
        if item not in from_node_name and item not in independent_variables_name:  #SO, IF IT DOESN'T APPEAR IN THE FROM DICTIONARY, SO IT'S NOT AFFECTED FROM NOTHING
            independent_variables_name.append(item)
    independent_variables_data = []
    for item in input.pairs:
        if item.to_.name_id in independent_variables_name and item.to_ not in independent_variables_data:
            independent_variables_data.append(item.to_)
    dependent_variables_name = []
    for item in variables_name:
        if item not in independent_variables_name and item not in targets_name_ids and item not in dependent_variables_name:
            dependent_variables_name.append(item)
    dependent_variables_data = []
    for item in input.pairs:
        if item.from_.name_id in dependent_variables_name and item.from_ not in dependent_variables_data:
            dependent_variables_data.append(item.from_)
    
    print(f"🔍 divide_dependent_independent results:")
    print(f"   - targets: {len(input.targets)}")
    print(f"   - dependent_variables: {len(dependent_variables_data)}")
    print(f"   - independent_variables: {len(independent_variables_data)}")
    
    return input.targets, dependent_variables_data, independent_variables_data


async def build_recommendation_schema(name_ids: List[str], plant_id: str) -> RecommendationCalculationEngineSchema:
    """
    Build complete RecommendationCalculationEngineSchema with pairs and targets.
    This is useful for manual AI requests where we need the full schema.
    """
    query = RECOMMENDATION_TEMPLATE.format(name_ids=name_ids)
    res = await execute_neo4j_query(query, plant_id)
    
    # Build targets
    targets = [RecommendationTargetEntitySchema(name_id=name_id) for name_id in name_ids]
    calc_engine_request = RecommendationCalculationEngineSchema(pairs=res, targets=targets, label="recommendations")
    
    # Populate with TimescaleDB values
    ts_name_ids = set(name_ids)
    for pair in calc_engine_request.pairs:
        ts_name_ids.add(pair.from_.name_id)
        for key in pair.from_.model_fields.keys():
            field = getattr(pair.from_, key)
            if isinstance(field, RecommendationEntitySchema):
                ts_name_ids.add(field.name_id)
            elif isinstance(field, list):
                for elem in field:
                    if isinstance(elem, RecommendationLimitEntitySchema):
                        ts_name_ids.add(elem.name_id)
        
        ts_name_ids.add(pair.to_.name_id)
        for key in pair.to_.model_fields.keys():
            field = getattr(pair.to_, key)
            if isinstance(field, RecommendationEntitySchema):
                ts_name_ids.add(field.name_id)
            elif isinstance(field, list):
                for elem in field:
                    if isinstance(elem, RecommendationLimitEntitySchema):
                        ts_name_ids.add(elem.name_id)
    
    # Query TimescaleDB
    ts_name_ids_str = ",".join(["'" + str(elem) + "'" for elem in ts_name_ids])
    ts_name_ids_str = f"({ts_name_ids_str})"
    ts_query = f"""
    select distinct on(tags.name) tags.name, tags.unit_of_measure, ts.value, ts.timestamp
    from time_series ts
    inner join tags on ts.tag_id = tags.id
    where tags.name in {ts_name_ids_str}
    order by tags.name, ts.timestamp desc
    """
    
    query_service = QueryService()
    async for db_session in get_plant_db(plant_id):
        res_ts, _, _ = await query_service.execute_query(db_session, ts_query)
    
    ts_res = {elem["name"]: {"unit_of_measure": elem["unit_of_measure"], "value": round(float(elem["value"]), 2), "timestamp": elem["timestamp"].strftime('%Y-%m-%d %H:%M')} for elem in res_ts}
    
    # Fill targets
    for target in calc_engine_request.targets:
        target.current_value = ts_res[target.name_id]["value"]
        target.unit_of_measurement = ts_res[target.name_id]["unit_of_measure"]
        target.timestamp = str(ts_res[target.name_id]["timestamp"])
    
    # Fill pairs
    for pair in calc_engine_request.pairs:
        pair.from_.current_value = ts_res[pair.from_.name_id]["value"]
        pair.from_.unit_of_measurement = ts_res[pair.from_.name_id]["unit_of_measure"]
        for key in pair.from_.model_fields.keys():
            field = getattr(pair.from_, key)
            if isinstance(field, RecommendationEntitySchema):
                field.current_value = ts_res[field.name_id]["value"]
                field.unit_of_measurement = ts_res[field.name_id]["unit_of_measure"]
            elif isinstance(field, list):
                for elem in field:
                    if isinstance(elem, RecommendationLimitEntitySchema):
                        elem.current_value = ts_res[elem.name_id]["value"]
                        elem.unit_of_measurement = ts_res[elem.name_id]["unit_of_measure"]
        
        pair.to_.current_value = ts_res[pair.to_.name_id]["value"]
        pair.to_.unit_of_measurement = ts_res[pair.to_.name_id]["unit_of_measure"]
        for key in pair.to_.model_fields.keys():
            field = getattr(pair.to_, key)
            if isinstance(field, RecommendationEntitySchema):
                field.current_value = ts_res[field.name_id]["value"]
                field.unit_of_measurement = ts_res[field.name_id]["unit_of_measure"]
            elif isinstance(field, list):
                for elem in field:
                    if isinstance(elem, RecommendationLimitEntitySchema):
                        elem.current_value = ts_res[elem.name_id]["value"]
                        elem.unit_of_measurement = ts_res[elem.name_id]["unit_of_measure"]
    
    logger.info(f"✅ Built recommendation schema with {len(calc_engine_request.pairs)} pairs and {len(calc_engine_request.targets)} targets")
    return calc_engine_request


async def build_execute_recommendation_query(name_ids: List[str], plant_id: str) -> Tuple[List[RecommendationPairElemSchema], List[RecommendationPairElemSchema]]:
    """
    Build and execute the recommendation query
    """
    query = RECOMMENDATION_TEMPLATE.format(name_ids=name_ids)
    # let's execute the query
    ############################################ read_query return a list of dict or []
    # ==========================================
    # TODO: implement the execute query on the KG
    # ==========================================
    res = await execute_neo4j_query(query,plant_id)
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
    select distinct on(tags.name) tags.name, tags.unit_of_measure, ts.value, ts.timestamp
    from time_series ts
    inner join tags on ts.tag_id = tags.id
    where tags.name in {ts_name_ids_str}
    order by tags.name, ts.timestamp desc
    """
    ############################################
    # Execute TimescaleDB query using QueryService
    query_service = QueryService()
    async for db_session in get_plant_db(plant_id):
        res, _, _ = await query_service.execute_query(db_session, ts_query)
    ############################################
    # let's build for efficiency a dictionary out of the list of resulting rows
    ts_res = {elem["name"]: {"unit_of_measure":elem["unit_of_measure"],"value":round(float(elem["value"]),2),"timestamp":elem["timestamp"].strftime('%Y-%m-%d %H:%M')} for elem in res}
            # let's check taht each target is present in the ts_res and has a valid value 
    # now we can populate the calc_engine_request with the Timescale values
    # first let's fill the targets
    for target in calc_engine_request.targets:
        target.current_value = ts_res[target.name_id]["value"]
        target.unit_of_measurement = ts_res[target.name_id]["unit_of_measure"]
        target.timestamp = str(ts_res[target.name_id]["timestamp"])
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
    print(f"🔧 CALLING divide_dependent_independent with {len(calc_engine_request.pairs)} pairs")
    calc_engine_result = divide_dependent_independent(calc_engine_request)
    print(f"✅ divide_dependent_independent returned: {type(calc_engine_result)}")
    if calc_engine_result and len(calc_engine_result) == 3:
        print(f"   - targets: {len(calc_engine_result[0]) if calc_engine_result[0] else 0}")
        print(f"   - dependent: {len(calc_engine_result[1]) if calc_engine_result[1] else 0}")
        print(f"   - independent: {len(calc_engine_result[2]) if calc_engine_result[2] else 0}")
        return calc_engine_result
    else:
        print("❌ divide_dependent_independent returned invalid result")
        return input.targets, [], []
    ############################################

async def execute_neo4j_query(query:str,plant_id:str)->List[dict]:
    """
    Execute a Neo4j query and return the result
    """
    kg = KnowledgeGraph(plant_id)
    res = []
    async for session in kg.get_session():
        neo4j_result = await kg.read_query(query, session)
        print(f"🔍 NEO4J QUERY RESULT: {neo4j_result}")
        if neo4j_result:
            res = [pair["pair"] for pair in neo4j_result]
        else:
            print("⚠️ No results from Neo4j query")
            res = []
    return res

def finish_calc_engine_request(target_values:Dict[str,float],calc_engine_request:RecommendationCalculationEngineSchema):
    # target value is a dict containg the targets_name_id as key and their inputted targets value as value
    for target in calc_engine_request.targets:
        target.target_value = target_values[target.name_id]
    ############################################
    # return calc_engine_request to the AI engine with a call to CHAT-LESS AI
    ############################################
    pass


def update_pairs(
    new_limits_value: Dict[str, float], 
    pairs: List[RecommendationCalculationEnginePairSchema]
) -> List[RecommendationCalculationEnginePairSchema]:
    """
    Update pairs with new limits values.
    
    Args:
        new_limits_value: Dictionary mapping limit name_ids to their new values
        pairs: List of pairs to update
    
    Returns:
        Updated list of pairs
    """
    logger.info(f"🔄 Updating pairs with {len(new_limits_value)} new limit values")
    
    # Validate pairs using TypeAdapter
    pairs = TypeAdapter(List[RecommendationCalculationEnginePairSchema]).validate_python(pairs)
    
    # Iterate through each pair
    for pair in pairs:
        # Get the from_ and to_ nodes
        from_ = pair.from_
        to_ = pair.to_
        
        # Collect all limits from both nodes
        limits = [from_.high_limits, to_.high_limits, from_.low_limits, to_.low_limits]
        
        # Update each limit if its name_id is in new_limits_value
        for limit_type in limits:
            if limit_type is not None:
                for limit in limit_type:
                    if limit.name_id in new_limits_value:
                        old_value = limit.current_value
                        limit.current_value = new_limits_value[limit.name_id]
                        logger.info(f"   ✅ Updated {limit.name_id}: {old_value} -> {limit.current_value}")
    
    logger.info(f"✅ Pairs updated successfully")
    return pairs


