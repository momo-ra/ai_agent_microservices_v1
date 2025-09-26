
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
