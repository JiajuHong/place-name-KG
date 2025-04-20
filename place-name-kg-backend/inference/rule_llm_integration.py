"""
规则和大模型集成的推理引擎
结合规则库和大模型能力进行推理，为地名实体提供智能问答
"""
import os
import json
import time
import ollama
from typing import List, Dict, Any, Optional, Tuple


class RuleLLMIntegration:
    """
    规则和大模型集成的推理引擎
    结合规则库和大语言模型的能力，基于知识图谱进行推理
    """
    
    def __init__(self, rule_file_path: str = 'rules/rule_base.json', 
                 model_name: str = "deepseek-r1:7b",
                 max_depth: int = 3):
        """
        初始化推理引擎
        
        Args:
            rule_file_path: 规则库文件路径
            model_name: 使用的大模型名称
            max_depth: 图谱搜索的最大深度
        """
        self.model_name = model_name
        self.max_depth = max_depth
        
        # 加载规则库
        self.rules = self._load_rules(rule_file_path)
        self.rule_id_map = {rule['rule_id']: rule for rule in self.rules}
        
        # 规则分类缓存，用于快速查找
        self._build_rule_indices()
        
        print(f"规则与大模型推理引擎已初始化, 使用模型: {model_name}, 规则数量: {len(self.rules)}")
    
    def _load_rules(self, rule_file_path: str) -> List[Dict]:
        """加载规则库"""
        try:
            with open(rule_file_path, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            print(f"成功加载规则库，共 {len(rules)} 条规则")
            return rules
        except Exception as e:
            print(f"加载规则库失败: {str(e)}")
            return []
    
    def _build_rule_indices(self):
        """构建规则索引，方便后续查找"""
        # 按关系类型索引
        self.relation_type_rules = {}
        # 按具体关系索引
        self.relation_rules = {}
        # 按复合规则索引
        self.composite_rules = []
        
        for rule in self.rules:
            # 检查是否是复合规则
            if 'composite' in rule.get('condition', {}) and rule['condition']['composite']:
                self.composite_rules.append(rule)
                continue
            
            # 按关系类型索引
            if 'relation_type' in rule.get('condition', {}):
                rel_type = rule['condition']['relation_type']
                if rel_type not in self.relation_type_rules:
                    self.relation_type_rules[rel_type] = []
                self.relation_type_rules[rel_type].append(rule)
            
            # 按具体关系索引
            if 'relation' in rule.get('condition', {}):
                relation = rule['condition']['relation']
                if relation not in self.relation_rules:
                    self.relation_rules[relation] = []
                self.relation_rules[relation].append(rule)
        
        print(f"规则索引构建完成: {len(self.relation_type_rules)} 种关系类型, "
              f"{len(self.relation_rules)} 种具体关系, {len(self.composite_rules)} 条复合规则")
    
    def _find_applicable_rules(self, relation_type: Optional[str] = None, 
                              relation: Optional[str] = None) -> List[Dict]:
        """
        查找适用于给定关系类型和关系的规则
        
        Args:
            relation_type: 关系类型
            relation: 具体关系
            
        Returns:
            适用规则列表
        """
        applicable_rules = []
        
        # 按关系类型查找
        if relation_type and relation_type in self.relation_type_rules:
            applicable_rules.extend(self.relation_type_rules[relation_type])
        
        # 按具体关系查找
        if relation and relation in self.relation_rules:
            applicable_rules.extend(self.relation_rules[relation])
        
        # 按优先级排序
        if applicable_rules:
            applicable_rules.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return applicable_rules
    
    def get_entity_relationships(self, entity_id: int, neo4j_db) -> List[Dict]:
        """
        获取实体的关系
        
        Args:
            entity_id: 实体ID
            neo4j_db: Neo4j数据库实例
            
        Returns:
            关系列表
        """
        try:
            # 获取出向关系
            query_outgoing = f"""
            MATCH (n)-[r]->(m)
            WHERE ID(n) = {entity_id}
            RETURN n, r, m, 'outgoing' as direction
            """
            
            # 获取入向关系
            query_incoming = f"""
            MATCH (n)<-[r]-(m)
            WHERE ID(n) = {entity_id}
            RETURN n, r, m, 'incoming' as direction
            """
            
            # 合并结果
            results_outgoing = neo4j_db.graph.run(query_outgoing).data()
            results_incoming = neo4j_db.graph.run(query_incoming).data()
            
            relationships = []
            processed_relations = set()  # 用于去重
            
            # 处理所有结果
            for result in results_outgoing + results_incoming:
                source_node = result['n'] if result['direction'] == 'outgoing' else result['m']
                target_node = result['m'] if result['direction'] == 'outgoing' else result['n']
                relation = result['r']
                
                # 创建关系的唯一标识，避免重复
                relation_id = f"{source_node.identity}_{target_node.identity}_{type(relation).__name__}"
                if relation_id in processed_relations:
                    continue
                
                processed_relations.add(relation_id)
                
                rel_type = type(relation).__name__
                
                rel_info = {
                    'source': {
                        'id': source_node.identity,
                        'name': source_node.get('name', ''),
                        'type': list(source_node.labels)[0] if source_node.labels else ''
                    },
                    'target': {
                        'id': target_node.identity,
                        'name': target_node.get('name', ''),
                        'type': list(target_node.labels)[0] if target_node.labels else ''
                    },
                    'relation': rel_type,
                    'properties': {k: v for k, v in relation.items()},
                    'direction': result['direction']
                }
                relationships.append(rel_info)
            
            print(f"获取到实体ID({entity_id})的 {len(relationships)} 个关系")
            return relationships
        except Exception as e:
            print(f"获取实体关系时出错: {str(e)}")
            return []
    
    def search_paths_between_entities(self, entity1_id: int, entity2_id: int, 
                                     neo4j_db, max_depth: Optional[int] = None) -> List[Dict]:
        """
        搜索两个实体之间的路径
        
        Args:
            entity1_id: 第一个实体ID
            entity2_id: 第二个实体ID
            neo4j_db: Neo4j数据库实例
            max_depth: 最大搜索深度
            
        Returns:
            路径列表
        """
        if max_depth is None:
            max_depth = self.max_depth
            
        try:
            # 查询从entity1到entity2的有向路径
            query_forward = f"""
            MATCH path = shortestPath((n)-[*1..{max_depth}]->(m))
            WHERE ID(n) = {entity1_id} AND ID(m) = {entity2_id}
            RETURN path
            LIMIT 5
            """
            
            # 查询从entity2到entity1的有向路径
            query_backward = f"""
            MATCH path = shortestPath((n)-[*1..{max_depth}]->(m))
            WHERE ID(n) = {entity2_id} AND ID(m) = {entity1_id}
            RETURN path
            LIMIT 5
            """
            
            # 合并结果
            results = []
            forward_results = neo4j_db.graph.run(query_forward).data()
            backward_results = neo4j_db.graph.run(query_backward).data()
            
            # 如果有正向路径，优先使用正向路径
            if forward_results:
                results = forward_results
            elif backward_results:
                results = backward_results
            
            paths = []
            for result in results:
                path = result.get('path')
                if not path:
                    continue
                    
                nodes = list(path.nodes)
                rels = list(path.relationships)
                
                path_data = []
                last_node_name = None
                last_node_id = None
                
                for i, node in enumerate(nodes):
                    node_data = {
                        'name': node['name'],
                        'id': node.identity,
                        'type': list(node.labels)[0] if node.labels else ''
                    }
                    
                    # 添加所有节点属性
                    for key, value in node.items():
                        if key != 'name' and key != 'id' and key != 'type':
                            node_data[key] = value
                    
                    # 添加关系信息
                    if i > 0 and i-1 < len(rels):
                        rel = rels[i-1]
                        rel_type = type(rel).__name__
                        
                        if rel.start_node.identity == last_node_id:
                            node_data['relation'] = f"{last_node_name} -{rel_type}-> {node['name']}"
                            node_data['relation_direction'] = 'outgoing'
                        else:
                            node_data['relation'] = f"{last_node_name} <-{rel_type}- {node['name']}"
                            node_data['relation_direction'] = 'incoming'
                        
                        node_data['relation_type'] = rel_type
                        node_data['relation_properties'] = {k: v for k, v in rel.items()}
                    
                    last_node_name = node['name']
                    last_node_id = node.identity
                    path_data.append(node_data)
                
                paths.append({
                    'path': path_data,
                    'length': len(rels),
                    'start_entity': path_data[0]['name'] if path_data else None,
                    'end_entity': path_data[-1]['name'] if path_data else None
                })
            
            print(f"找到 {len(paths)} 条从 {entity1_id} 到 {entity2_id} 的路径")
            return paths
            
        except Exception as e:
            print(f"搜索路径时出错: {str(e)}")
            return []
    
    def apply_inference_rules(self, relationships: List[Dict]) -> List[Dict]:
        """应用推理规则，生成新的关系"""
        inferred_relationships = []
        
        for rel in relationships:
            # 使用原始关系（非格式化）来匹配规则
            # 先获取关系名称，优先使用relation属性（如果存在）
            relation_type = rel.get('properties', {}).get('relation_type', '')

            time = rel.get('properties', {}).get('time', '')
            
            # 从properties中获取原始的relation（非格式化），这是由data_process添加的
            relation = rel.get('properties', {}).get('relation', '')
            
            # 如果原始relation不存在，则使用关系类型作为后备
            if not relation:
                relation = rel.get('relation', '')
                
            source_name = rel.get('source', {}).get('name', '')
            target_name = rel.get('target', {}).get('name', '')
            
            # 跳过已经是推理关系的条目，避免重复推理
            if rel.get('properties', {}).get('inferred', False):
                continue
            
            # 分类规则：大类规则和细分规则
            big_category_rules = []  # 大类规则（演变类、所属类）
            specific_rules = []      # 细分规则
            
            # 获取可应用的规则
            for rule in self.rules:
                condition = rule.get('condition', {})
                # 跳过复合规则
                if condition.get('composite', False):
                    continue
                    
                rule_relation_type = condition.get('relation_type', '')
                rule_relation = condition.get('relation', '')
                
                # 大类规则匹配（只需匹配relation_type，对演变类和所属类）
                if rule_relation_type in ["演变类", "所属类"] and rule_relation_type == relation_type:
                    if not rule_relation or rule_relation == relation:
                        big_category_rules.append(rule)
                
                # 细分规则匹配（优先完全匹配，其次只匹配relation）
                elif rule_relation:
                    if rule_relation == relation:
                        # 如果规则有relation_type且与关系不匹配，则跳过
                        if rule_relation_type and rule_relation_type != relation_type:
                            continue
                        specific_rules.append(rule)
            
            # 合并大类规则和细分规则，确保至少应用大类规则
            applicable_rules = big_category_rules + specific_rules
            
            # 如果没有适用的规则，跳过
            if not applicable_rules:
                continue
            
            # 应用规则
            for rule in applicable_rules:
                # 获取规则的推理部分
                inference = rule.get('inference', {})
                inferred_relation = inference.get('relation', '')
                direction = inference.get('direction', 'forward')
                
                # 获取规则中定义的原始关系作为derived_from
                rule_relation = rule.get('condition', {}).get('relation', '')
                if not rule_relation:
                    # 如果规则没有定义具体关系，使用数据关系
                    rule_relation = relation
                
                # 创建新关系
                inferred_rel = {
                    'source': {
                        'id': rel['source']['id'],
                        'name': rel['source']['name'],
                        'type': rel['source']['type']
                    },
                    'target': {
                        'id': rel['target']['id'],
                        'name': rel['target']['name'],
                        'type': rel['target']['type']
                    },
                    'relation': inferred_relation,
                    'properties': {
                        'inferred': True,
                        'rule_id': rule['rule_id'],
                        'rule_name': rule.get('name', ''),
                        'derived_from': relation,
                        'time': time
                    }
                }
                
                # 处理方向 - 修复演变类关系方向问题
                if relation_type == "演变类":
                    # 对于演变类关系，数据已在导入时做过方向反转
                    # 因此关系方向是：被演变实体 -> 演变而来的实体
                    # 例如：平江府 -> 平江路，表示平江路演变自平江府
                    # 查看data_process.py，演变类关系存储为：关联实体(node2) -> 实体名称(node1)
                    
                    # 如果推理规则是forward方向，表示保持方向一致
                    # 对于演变于/演变自关系，应该是：source(被演变的) -> target(演变而来的)
                    if direction == "forward":
                        # 对于forward规则，保持原有方向
                        pass
                    else:
                        # 对于reverse规则，反转方向
                        inferred_rel['source'], inferred_rel['target'] = inferred_rel['target'], inferred_rel['source']
                elif relation_type == "所属类":
                    # 所属类中，实际数据存储是 A--所属类关系-->B，
                    # 表示 A 隶属于 B，B 下辖 A
                    if direction == "reverse":
                        # 反转关系方向
                        inferred_rel['source'], inferred_rel['target'] = inferred_rel['target'], inferred_rel['source']
                else:
                    # 处理其他类型关系或未指定类型关系
                    if direction == "reverse":
                        inferred_rel['source'], inferred_rel['target'] = inferred_rel['target'], inferred_rel['source']
                
                # 在关系对象上添加inferred标记，便于前端识别
                inferred_rel['inferred'] = True
                
                # 记录处理日志
                print(f"推理关系: {inferred_rel['source']['name']} --[{inferred_relation}]--> {inferred_rel['target']['name']}")
                print(f"  基于原始关系: {source_name} --[{relation}]--> {target_name}")
                print(f"  关系类型: {relation_type}, 规则: {rule.get('name', '')}")
                print(f"  规则定义的关系: {rule_relation}")
                
                inferred_relationships.append(inferred_rel)
        
        print(f"根据规则推理出 {len(inferred_relationships)} 个新关系")
        return inferred_relationships
    
    def _build_inference_prompt(self, 
                               question: str,
                               entities: List[str],
                               entity_info: List[Dict],
                               relationships: List[Dict],
                               paths: List[Dict]) -> str:
        """构建推理提示词"""
        
        # 格式化实体信息为文本
        entity_info_text = ""
        for i, info in enumerate(entity_info):
            if info:
                properties = info.get('properties', {})
                props_text = ", ".join([f"{k}: {v}" for k, v in properties.items() if k != 'name'])
                entity_info_text += f"{i+1}. {info.get('name', '')} (类型: {info.get('type', '未知')})"
                if props_text:
                    entity_info_text += f", 属性: {props_text}"
                entity_info_text += "\n"
        
        # 分离原始关系和推理关系
        original_relationships = []
        inferred_relationships = []
        
        for rel in relationships:
            if rel.get('properties', {}).get('inferred', False) or rel.get('inferred', False):
                inferred_relationships.append(rel)
            else:
                original_relationships.append(rel)
        
        # 格式化关系信息为文本
        relationships_text = "原始关系(直接来自知识图谱):\n"
        for i, rel in enumerate(original_relationships):
            source = rel.get('source', {}).get('name', '')
            target = rel.get('target', {}).get('name', '')
            relation = rel.get('relation', '')
            relationships_text += f"{i+1}. {source} --[{relation}]--> {target}\n"
        
        relationships_text += "\n推理关系(通过规则推理生成):\n"
        for i, rel in enumerate(inferred_relationships):
            source = rel.get('source', {}).get('name', '')
            target = rel.get('target', {}).get('name', '')
            relation = rel.get('relation', '')
            relationships_text += f"{i+1}. {source} --[{relation}]--> {target}\n"
        
        # 格式化路径信息为文本
        paths_text = ""
        for i, path_data in enumerate(paths):
            path = path_data.get('path', [])
            if path:
                path_str = path[0].get('name', '')
                for j in range(1, len(path)):
                    node = path[j]
                    relation = node.get('relation_type', '')
                    path_str += f" --[{relation}]--> {node.get('name', '')}"
                paths_text += f"{i+1}. {path_str}\n"
        
        # 构建完整提示词
        prompt = f"""你是一个专业的中国历史地名专家，精通地名沿革、行政区划变迁和地理位置关系。

在分析地名关系时，请注意以下重要规则：
1. 演变类关系表示地名的历史演变，A --[演变类]--> B 意味着"A演变为B"
2. 推理关系是基于原始关系推导出的，应当与原始关系结合分析

请确保你的回答：
- 准确反映地名的历史演变顺序
- 正确解读行政隶属关系
- 清晰区分原始关系和推理关系
- 基于证据推理，如无明确证据，说明这是推测

所有回答必须基于知识图谱提供的事实，不要添加图谱之外的历史信息。

用户问题: {question}

识别到的地名实体: {', '.join(entities) if entities else '无'}

实体详情:
{entity_info_text if entity_info_text else '无可用实体详情'}

实体关系 (注意: A--[演变类]-->B 表示"A演变为B"):
{relationships_text if relationships_text else '无可用实体关系'}

实体之间的路径 (从源实体到目标实体的关系链):
{paths_text if paths_text else '无可用路径信息'}

基于上述地名知识图谱中的信息，请分析并回答用户问题。如果信息不足以完全回答，可以进行合理推测，但必须明确标明哪些是基于图谱的事实，哪些是你的推测。

分析思路：
1. 首先分析问题类型(是查询地名变迁、行政隶属关系、地理位置还是其他)
2. 分析图谱中与问题相关的关键实体及其属性
3. 分析实体间的直接关系和路径，特别关注演变类和所属类关系
4. 整合直接关系和推理关系，形成完整的地名关系链
5. 基于上述分析形成最终答案

回答时先简要思考，然后给出准确清晰的结论。

分析信息时请遵循以下优先级:
1. 直接来自知识图谱的原始关系具有最高可信度
2. 基于原始关系的一阶推理关系次之
3. 如有冲突，请优先采信原始关系

请在回答中明确指出你使用的是原始关系还是推理关系。

回答中请说明你的推理路径，特别是当你依赖推理关系时，请指出这是基于何种原始关系推导出的。

请对你的推理进行自我验证:
1. 检查时间顺序是否合理（地名演变应遵循历史顺序）
2. 验证行政隶属关系的层级是否合理
3. 确认你的结论同时满足图谱中的原始关系和推理关系
"""
        
        return prompt
    
    def generate_response_with_llm(self, 
                                  question: str,
                                  entities: List[str],
                                  entity_info: List[Dict],
                                  relationships: List[Dict],
                                  paths: List[Dict]) -> str:
        """
        使用大模型生成回答
        
        Args:
            question: 用户问题
            entities: 实体列表
            entity_info: 实体信息列表
            relationships: 关系列表
            paths: 路径列表
            
        Returns:
            生成的回答
        """
        # 构建提示词
        prompt = self._build_inference_prompt(
            question=question,
            entities=entities,
            entity_info=entity_info,
            relationships=relationships,
            paths=paths
        )
        
        try:
            # 记录模型调用开始时间
            start_time = time.time()
            print(f"调用 {self.model_name} 模型生成回答...")
            
            # 调用大模型生成回答
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": """你是一个专业的中国历史地名专家，精通地名沿革、行政区划变迁和地理位置关系。

请遵循以下解读原则：
1. 演变类关系(A→B)表示A演变为B，即A是历史较早的地名，B是后来的地名
2. 所属类关系(A→B)表示A隶属于B，即B是上级行政区，A是其下辖区域。
3. 特别的，如果A--下辖-->B，则B是A的下一级行政区，A是B的上级行政区。
3. 距离类关系表示地理位置距离

分析要求：
- 严格基于知识图谱提供的实体和关系进行分析
- 对于多条可能的演变路径，优先考虑最直接的关系
- 指出推理关系与原始关系的区别
- 识别并说明时间维度上的演变序列


回答要专业、准确且易于理解，避免出现与图谱事实不符的内容。"""
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                stream=False,
                options={"temperature": 0.1}  # 添加低温度参数
            )
            
            # 记录模型调用耗时
            process_time = time.time() - start_time
            print(f"模型响应成功，耗时: {process_time:.2f}秒")
            
            # 返回模型生成的回答
            return response['message']['content']
            
        except Exception as e:
            print(f"模型调用失败: {str(e)}")
            return f"抱歉，在处理您的问题时遇到了技术问题。错误信息: {str(e)}"
    
    def process_question(self, question: str, entity_extractor, neo4j_db) -> Dict:
        """
        处理用户问题，返回推理结果
        
        Args:
            question: 用户问题
            entity_extractor: 实体提取器实例
            neo4j_db: Neo4j数据库实例
            
        Returns:
            包含回答和可视化数据的字典
        """
        start_time = time.time()
        
        try:
            print(f"开始处理用户问题: '{question}'")
            
            # 1. 从问题中提取实体
            entities = entity_extractor.extract_entities(question)
            
            if not entities:
                return {
                    'answer': "抱歉，我无法从您的问题中识别出任何地名实体。请尝试提供更具体的地名。",
                    'entities': [],
                    'kg_data': {'nodes': [], 'lines': []},
                    'process_time': time.time() - start_time
                }
            
            # 记录查询涉及的所有节点和关系
            all_entity_info = []
            all_relationships = []
            all_paths = []
            
            # 2. 从知识图谱中查询实体信息
            entity_info_map = {}  # 实体ID到实体信息的映射
            for entity in entities:
                # 先进行精确查询
                query = f"""
                MATCH (n)
                WHERE n.name = '{entity}'
                RETURN n
                LIMIT 1
                """
                results = neo4j_db.graph.run(query).data()
                
                if results:
                    node = results[0]['n']
                    info = {
                        'id': node.identity,
                        'name': node['name'],
                        'type': list(node.labels)[0] if node.labels else '',
                        'properties': {k: v for k, v in node.items()}
                    }
                    all_entity_info.append(info)
                    entity_info_map[info['id']] = info
                else:
                    # 尝试模糊查询
                    fuzzy_query = f"""
                    MATCH (n)
                    WHERE n.name CONTAINS '{entity}' OR '{entity}' CONTAINS n.name
                    RETURN n
                    LIMIT 5
                    """
                    fuzzy_results = neo4j_db.graph.run(fuzzy_query).data()
                    
                    if fuzzy_results:
                        for result in fuzzy_results:
                            node = result['n']
                            info = {
                                'id': node.identity,
                                'name': node['name'],
                                'type': list(node.labels)[0] if node.labels else '',
                                'properties': {k: v for k, v in node.items()}
                            }
                            all_entity_info.append(info)
                            entity_info_map[info['id']] = info
            
            # 3. 获取实体关系
            for info in all_entity_info:
                entity_id = info['id']
                relationships = self.get_entity_relationships(entity_id, neo4j_db)
                all_relationships.extend(relationships)
            
            # 4. 搜索实体之间的路径
            if len(all_entity_info) >= 2:
                for i in range(len(all_entity_info)):
                    for j in range(i+1, len(all_entity_info)):
                        entity1_id = all_entity_info[i]['id']
                        entity2_id = all_entity_info[j]['id']
                        paths = self.search_paths_between_entities(entity1_id, entity2_id, neo4j_db)
                        all_paths.extend(paths)
            
            # 5. 应用推理规则
            inferred_relationships = self.apply_inference_rules(all_relationships)
            
            # 原始关系与推理关系分开处理
            original_relationships = all_relationships.copy()
            all_relationships.extend(inferred_relationships)
            
            # 6. 使用大模型生成回答
            answer = self.generate_response_with_llm(
                question=question,
                entities=entities,
                entity_info=all_entity_info,
                relationships=all_relationships,
                paths=all_paths
            )
            
            # 7. 构建知识图谱可视化数据（只使用原始关系，不含推理关系）
            kg_data = self._convert_to_visual_data(all_entity_info, original_relationships, all_paths)
            
            # 8. 格式化关系数据为三元组格式（包含原始和推理关系，但推理关系明确标注）
            context = self._format_relations_for_context(original_relationships, inferred_relationships)
            
            process_time = time.time() - start_time
            print(f"问题处理完成，总耗时: {process_time:.2f}秒")
            
            return {
                'answer': answer,
                'entities': entities,
                'kg_data': kg_data,
                'context': context,  # 添加格式化后的关系上下文
                'process_time': process_time
            }
            
        except Exception as e:
            print(f"处理问题时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'answer': f"抱歉，处理您的问题时遇到了技术问题: {str(e)}",
                'entities': entities if 'entities' in locals() else [],
                'kg_data': {'nodes': [], 'lines': []},
                'error': str(e),
                'process_time': time.time() - start_time
            }
    
    def _convert_to_visual_data(self, entities, relationships, paths):
        """将实体、关系和路径转换为可视化数据格式"""
        nodes = []
        lines = []
        node_ids = set()
        line_pairs = set()  # 使用无序对记录关系，避免方向重复
        
        # 添加实体节点
        for entity in entities:
            if entity['id'] not in node_ids:
                nodes.append({
                    'id': entity['id'],
                    'name': entity['name'],
                    'type': entity['type']
                })
                node_ids.add(entity['id'])
        
        # 添加路径中的节点和关系
        for path_data in paths:
            path = path_data.get('path', [])
            last_node = None
            
            for i, node in enumerate(path):
                # 添加节点
                node_id = node.get('id')
                if node_id not in node_ids:
                    node_data = {
                        'id': node_id,
                        'name': node.get('name', '未命名'),
                        'type': node.get('type', '')
                    }
                    nodes.append(node_data)
                    node_ids.add(node_id)
                
                # 添加关系（从第二个节点开始）
                if i > 0 and last_node:
                    # 获取关系信息
                    relation_type = node.get('relation_type', '')
                    from_id = last_node.get('id')
                    to_id = node_id
                    
                    # 创建关系的唯一标识（排序后的ID对+关系类型）
                    relation_key = (min(from_id, to_id), max(from_id, to_id), relation_type)
                    
                    # 检查关系是否已存在
                    if relation_key not in line_pairs:
                        line_data = {
                            'from': from_id,
                            'to': to_id,
                            'text': relation_type,
                            'relation_direction': node.get('relation_direction', 'outgoing')
                        }
                        lines.append(line_data)
                        line_pairs.add(relation_key)
                
                last_node = node
        
        # 存储唯一的关系ID，用于去重
        relation_ids = set()
        
        # 添加所有关系，包括数据库关系和推理关系
        for rel in relationships:
            from_id = rel['source']['id']
            to_id = rel['target']['id']
            relation_type = rel['relation']
            
            # 确保节点存在
            if from_id not in node_ids:
                nodes.append({
                    'id': from_id,
                    'name': rel['source']['name'],
                    'type': rel['source']['type']
                })
                node_ids.add(from_id)
            
            if to_id not in node_ids:
                nodes.append({
                    'id': to_id,
                    'name': rel['target']['name'],
                    'type': rel['target']['type']
                })
                node_ids.add(to_id)
            
            # 创建唯一关系ID
            relation_id = f"{from_id}_{to_id}_{relation_type}"
            
            # 检查关系是否已存在
            if relation_id not in relation_ids:
                relation_ids.add(relation_id)
                
                line_data = {
                    'from': from_id,
                    'to': to_id,
                    'text': relation_type
                }
                
                # 添加关系属性
                if 'properties' in rel:
                    for k, v in rel['properties'].items():
                        line_data[k] = v
                
                # 添加关系方向
                if 'direction' in rel:
                    line_data['direction'] = rel['direction']
                
                # 标记是否为推理关系
                if rel.get('properties', {}).get('inferred', False):
                    line_data['inferred'] = True
                elif rel.get('inferred', False):
                    line_data['inferred'] = True
                
                lines.append(line_data)
        
        # 去除重复的反向关系
        unique_lines = []
        processed_pairs = set()
        
        for line in lines:
            from_id = line['from']
            to_id = line['to']
            relation_type = line['text']
            
            # 创建无序的实体对，用于检测反向关系
            entity_pair = tuple(sorted([from_id, to_id]))
            relation_key = (*entity_pair, relation_type)
            
            # 如果这个实体对的关系之前处理过，且不是推理关系，则跳过
            if relation_key in processed_pairs and not line.get('inferred', False):
                continue
            
            processed_pairs.add(relation_key)
            unique_lines.append(line)
        
        return {
            'nodes': nodes,
            'lines': unique_lines
        }
    
    def _format_relations_for_context(self, relations: List[Dict[str, Any]], inferred_relations: List[Dict[str, Any]]) -> str:
        """将关系信息格式化为易读的上下文信息"""
        text_parts = []
        
        # 添加标题和说明
        text_parts.append("# 知识图谱中的关系数据")
        text_parts.append("以下数据来自地名知识图谱\n")
        text_parts.append("演变类关系，即A--[演变类]-->B，则语义为：A演变为B。")
        
        
        if relations:
            text_parts.append("## 图谱中的直接关系")
            for i, relation in enumerate(relations):
                # 过滤掉可能混入的推理关系
                if relation.get("properties", {}).get("inferred", False):
                    continue
                
                source = relation.get("source", {}).get("name", "未知实体")
                target = relation.get("target", {}).get("name", "未知实体")
                relation_type = relation.get("relation", "未知关系")
                
                # 创建格式化的关系描述
                rel_desc = f"{i+1}. {source} --[{relation_type}（{target}演变为{source}）]--> {target}  【数据库关系】"
                
                # 添加额外属性信息
                extra_props = []
                
                # 实体类型信息
                source_type = relation.get("source", {}).get("type", "")
                if source_type:
                    extra_props.append(f"源实体类型: {source_type}")
                    
                target_type = relation.get("target", {}).get("type", "")
                if target_type:
                    extra_props.append(f"目标实体类型: {target_type}")
                
                # 关系属性
                rel_props = relation.get("properties", {})
                relation_attrs = []
                for key, value in rel_props.items():
                    if key not in ["inferred", "rule_id", "rule_name", "derived_from"] and value:
                        relation_attrs.append(f"{key}: {value}")
                
                if relation_attrs:
                    extra_props.append(f"关系属性: {', '.join(relation_attrs)}")
                
                # 添加属性信息（如果有）
                if extra_props:
                    props_text = " | ".join(extra_props)
                    rel_desc += f"\n   {props_text}"
                
                text_parts.append(rel_desc)
                
                # 添加分隔符（除了最后一个关系）
                if i < len(relations) - 1:
                    text_parts.append("---")
        
        if inferred_relations:
            text_parts.append("\n## 通过规则推理得出的关系")
            text_parts.append("这些关系是基于规则推理生成的，不存在于原始数据库中\n")
            
            for i, relation in enumerate(inferred_relations):
                source = relation.get("source", {}).get("name", "未知实体")
                target = relation.get("target", {}).get("name", "未知实体")
                relation_type = relation.get("relation", "未知关系")
                
                # 查找推理依据
                derived_from = relation.get("properties", {}).get("derived_from", "未知")
                time = relation.get("properties", {}).get("time", "")
                rule_name = relation.get("properties", {}).get("rule_name", "")
                rule_id = relation.get("properties", {}).get("rule_id", "")
                
                # 创建格式化的关系描述
                rel_desc = f"{i+1}. {source} --[{relation_type}]--> {target}  【推理关系】"
                
                # 添加推理信息
                inference_info = []
                if derived_from:
                    inference_info.append(f"基于关系: {time}_{derived_from}")
                if rule_name:
                    inference_info.append(f"应用规则: {rule_name}")
                if rule_id:
                    inference_info.append(f"规则ID: {rule_id}")
                
                if inference_info:
                    info_text = " | ".join(inference_info)
                    rel_desc += f"\n   {info_text}"
                
                text_parts.append(rel_desc)
                
                # 添加分隔符（除了最后一个关系）
                if i < len(inferred_relations) - 1:
                    text_parts.append("---")
        
        if not relations and not inferred_relations:
            return "未找到相关地名关系信息"
        
        return "\n".join(text_parts) 