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
            relation = rel.get('relation', '')
            relation_type = rel.get('properties', {}).get('relation_type', '')
            source_name = rel.get('source', {}).get('name', '')
            target_name = rel.get('target', {}).get('name', '')
            
            # 跳过已经是推理关系的条目，避免重复推理
            if rel.get('properties', {}).get('inferred', False):
                continue
            
            # 查找适用的规则
            applicable_rules = self._find_applicable_rules(
                relation_type=relation_type,
                relation=relation
            )
            
            # 应用规则
            for rule in applicable_rules:
                # 获取规则的推理部分
                inference = rule.get('inference', {})
                inferred_relation = inference.get('relation', '')
                direction = inference.get('direction', 'forward')
                
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
                        'derived_from': relation
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
        
        # 格式化关系信息为文本
        relationships_text = ""
        for i, rel in enumerate(relationships):
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
        prompt = f"""我需要你基于以下信息回答用户的问题。

用户问题: {question}

识别到的实体: {', '.join(entities) if entities else '无'}

实体详情:
{entity_info_text if entity_info_text else '无可用实体详情'}

实体关系:
{relationships_text if relationships_text else '无可用实体关系'}

实体之间的路径:
{paths_text if paths_text else '无可用路径信息'}

基于上述知识图谱中的信息，请直接回答用户的问题。如果信息不足以完全回答，可以进行合理推测，但要说明这是推测。
请使用专业、简洁的语言，不需要复述或总结知识图谱中的所有信息，只需提供与问题直接相关的信息。

回答应当遵循以下格式：

<think>
1. 问题理解: (简单重述用户问题并说明要分析的关键点)

2. 实体分析: (对识别到的各个实体进行简要分析)

3. 关系分析: (分析实体之间的关系)
</think>

4. 推理结论: (基于以上分析给出结论)

你的回答必须严格按照上述格式，用<think>标签包围思考过程，确保该标签单独占一行。推理结论作为最终回答直接展示给用户。
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
                        "content": "你是一个专业的地名历史专家，擅长解释地名沿革、地理位置和历史变迁。你的回答"
                                  "应当基于知识图谱中提供的实体和关系信息，保持专业、简洁和准确。"
                                  "你可以进行合理推测，但需要清晰说明这是推测。"
                                  "请使用清晰的语言回答用户问题，并按指定格式组织你的思考过程。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                stream=False
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
                rel_desc = f"{i+1}. {source} --[{relation_type}]--> {target}  【数据库关系】"
                
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
                rule_name = relation.get("properties", {}).get("rule_name", "")
                rule_id = relation.get("properties", {}).get("rule_id", "")
                
                # 创建格式化的关系描述
                rel_desc = f"{i+1}. {source} --[{relation_type}]--> {target}  【推理关系】"
                
                # 添加推理信息
                inference_info = []
                if derived_from:
                    inference_info.append(f"基于关系: {derived_from}")
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