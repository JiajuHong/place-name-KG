from py2neo import Graph, Node


class neo4j_db():
    '''neo4j的操作'''

    def __init__(self, uri="bolt://localhost:7687", user=None, password=None, **kwargs):
        # 设置默认认证信息
        if user is None:
            user = "neo4j"
        if password is None:
            password = "123456"
        
        self.graph = Graph(uri, user=user, password=password)
        
        # 直接设置APOC不可用，不进行检测
        self.apoc_available = False
        print("使用非APOC方式进行模糊匹配")

    def find_node_page(self, current, limit, name_query):
        # 计算分页参数
        skip = (current - 1) * limit
        # 构建Cypher查询
        match_clause = "MATCH (n)"
        where_clause = f"WHERE n.name CONTAINS '{name_query}'" if name_query else ""
        return_clause = "RETURN id(n), labels(n), n.name"
        order_by_clause = "ORDER BY n.name"
        skip_limit_clause = f"SKIP {skip} LIMIT {limit}"
        query = " ".join([match_clause, where_clause, return_clause, order_by_clause, skip_limit_clause])
        # 执行查询
        results = self.graph.run(query).data()
        # 获取总节点数（用于分页）
        if name_query:
            name_condition = f' {{name: "{name_query}"}}'
        else:
            name_condition = ''
        count_query = f"MATCH (n{name_condition}) RETURN count(DISTINCT n)"
        total_count = self.graph.run(count_query).evaluate() or 0
        # 返回结果
        nodes = []
        for record in results:
            node_id = record['id(n)']
            node_labels = record['labels(n)']
            node_name = record['n.name'] if 'n.name' in record else None
            nodes.append({
                "id": node_id,
                "type": node_labels[0],
                "name": node_name
            })

        return {
            "total": total_count,
            "records": nodes
        }

    # 创建节点
    def create_node(self, label, name):
        node = Node(label, name=name)
        self.graph.create(node)
        return node

    # 更新节点
    def update_node(self, label, node_id, new_name):
        sql = f'MATCH (n:`{label}`) where id(n)={node_id} RETURN n'
        result = self.graph.run(sql).data()
        if result:
            # 从字典中提取节点对象
            node = result[0]['n']
            node["name"] = new_name
            self.graph.push(node)

    # 获取节点详细信息
    def get_node_detail(self, node_id):
        """获取节点的所有属性"""
        sql = f'MATCH (n) WHERE id(n)={node_id} RETURN n, labels(n) as labels'
        result = self.graph.run(sql).data()
        if result:
            node = result[0]['n']
            labels = result[0]['labels']
            # 转换为字典格式
            node_properties = dict(node)
            # 添加ID和类型
            node_properties['id'] = node.identity
            node_properties['type'] = labels[0] if labels else ''
            return node_properties
        return None
    
    # 更新节点所有属性
    def update_node_properties(self, node_id, properties):
        """更新节点的所有属性"""
        # 移除id和type，这些不是节点属性
        prop_copy = {k: v for k, v in properties.items() if k not in ['id', 'type']}
        
        # 查询节点
        sql = f'MATCH (n) WHERE id(n)={node_id} RETURN n, labels(n) as labels'
        result = self.graph.run(sql).data()
        if result:
            node = result[0]['n']
            labels = result[0]['labels']
            
            # 先清除所有现有属性（除了内置属性）
            for key in list(node.keys()):
                if key != '__ogm__':  # 保留内部属性
                    del node[key]
            
            # 设置新属性
            for key, value in prop_copy.items():
                node[key] = value
            
            # 保存更改
            self.graph.push(node)
            return True
        return False

    # 删除节点
    def delete_node(self, label, node_id):
        sql = f'MATCH (n:`{label}`) where id(n)={node_id} RETURN n'
        result = self.graph.run(sql).data()
        if result:
            # 从字典中提取节点对象
            node = result[0]['n']
            self.graph.delete(node)

    def get_node_types(self):
        """获取所有节点类型"""
        query = """
        MATCH (n)
        RETURN DISTINCT labels(n) as types
        """
        results = self.graph.run(query)
        node_types = []
        for record in results:
            # 获取第一个标签作为节点类型
            if record['types']:
                node_types.append(record['types'][0])
        return sorted(node_types)

    def get_relationship_types(self):
        """获取所有关系类型"""
        query = """
        MATCH ()-[r]-()
        RETURN DISTINCT type(r) as type
        """
        results = self.graph.run(query)
        rel_types = []
        for record in results:
            if record['type']:
                rel_types.append(record['type'])
        return sorted(rel_types)

    def get_node_relations(self, node_id):
        """
        获取节点的所有直接关系
        :param node_id: 节点ID
        :return: 与节点直接相关的节点和关系
        """
        sql = f"""
        MATCH (n)-[r]-(m)
        WHERE id(n) = {node_id}
        RETURN n, r, m
        """
        result = self.graph.run(sql).data()
        
        nodes = []
        lines = []
        node_ids = set()
        
        # 加入中心节点
        center_node_sql = f"""
        MATCH (n)
        WHERE id(n) = {node_id}
        RETURN n
        """
        center_result = self.graph.run(center_node_sql).data()
        if center_result:
            center_node = center_result[0]['n']
            node_data = {
                'id': center_node.identity,
                'name': center_node['name'],
                'type': list(center_node.labels)[0] if center_node.labels else ''
            }
            nodes.append(node_data)
            node_ids.add(center_node.identity)
        
        for record in result:
            # 添加关联节点
            rel_node = record['m']
            if rel_node.identity not in node_ids:
                node_data = {
                    'id': rel_node.identity,
                    'name': rel_node['name'],
                    'type': list(rel_node.labels)[0] if rel_node.labels else ''
                }
                nodes.append(node_data)
                node_ids.add(rel_node.identity)
            
            # 添加关系
            rel = record['r']
            rel_type = type(rel).__name__
            
            # 构建关系数据
            line_data = {
                'from': rel.start_node.identity,
                'to': rel.end_node.identity,
                'text': rel_type
            }
            
            # 添加关系属性，包括关系类型
            for key, value in rel.items():
                line_data[key] = value
                
            # 特别处理关系类型属性
            if 'relation_type' in rel:
                line_data['relation_category'] = rel['relation_type']
            
            lines.append(line_data)
        
        return {"nodes": nodes, "lines": lines}
        
    def get_nodes_by_type(self, node_type):
        """
        根据节点类型获取节点列表
        :param node_type: 节点类型
        :return: 节点列表
        """
        sql = f"""
        MATCH (n:{node_type})
        RETURN n
        LIMIT 100
        """
        
        result = self.graph.run(sql).data()
        
        if not result:
            return {"nodes": [], "lines": []}
            
        nodes = []
        node_ids = set()
        
        for record in result:
            node = record['n']
            node_id = node.identity
            if node_id not in node_ids:
                node_data = {
                    'id': node_id,
                    'name': node['name'],
                    'type': node_type
                }
                nodes.append(node_data)
                node_ids.add(node_id)
            
        return {"nodes": nodes, "lines": []}
        
    def get_nodes_by_relationship(self, rel_type):
        """
        根据关系类型获取所有相关节点和关系
        :param rel_type: 关系类型
        :return: 相关节点和关系
        """
        # 直接使用关系类型名称，不添加额外的修饰
        sql = f"""
        MATCH (n)-[r]-(m)
        WHERE type(r) = '{rel_type}'
        RETURN n, r, m
        LIMIT 100
        """
        
        result = self.graph.run(sql).data()
        
        if not result:
            return {"nodes": [], "lines": []}
            
        nodes = []
        lines = []
        node_ids = set()
        
        for record in result:
            # 添加源节点
            source_node = record['n']
            if source_node.identity not in node_ids:
                source_data = {
                    'id': source_node.identity,
                    'name': source_node['name'],
                    'type': list(source_node.labels)[0] if source_node.labels else ''
                }
                nodes.append(source_data)
                node_ids.add(source_node.identity)
                
            # 添加目标节点
            target_node = record['m']
            if target_node.identity not in node_ids:
                target_data = {
                    'id': target_node.identity,
                    'name': target_node['name'],
                    'type': list(target_node.labels)[0] if target_node.labels else ''
                }
                nodes.append(target_data)
                node_ids.add(target_node.identity)
                
            # 添加关系
            rel = record['r']
            rel_type_name = type(rel).__name__
            
            # 构建关系数据
            line_data = {
                'from': rel.start_node.identity,
                'to': rel.end_node.identity,
                'text': rel_type_name
            }
            
            # 添加关系属性，包括关系类型
            for key, value in rel.items():
                line_data[key] = value
                
            # 特别处理关系类型属性
            if 'relation_type' in rel:
                line_data['relation_category'] = rel['relation_type']
            
            lines.append(line_data)
            
        return {"nodes": nodes, "lines": lines}


    def search_nodes_by_name(self, search_text, limit=100):
        """
        按节点名称进行模糊搜索
        :param search_text: 搜索文本
        :param limit: 返回结果数量限制
        :return: 匹配的节点列表
        """
        if not search_text:
            return {"nodes": [], "lines": []}
            
        try:
            # 构建模糊搜索查询
            search_text = search_text.replace("'", "\\'")  # 防止SQL注入
            
            cypher_query = f"""
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower('{search_text}') 
                  OR (n.alias IS NOT NULL AND toLower(n.alias) CONTAINS toLower('{search_text}'))
            RETURN n, 
                CASE 
                    WHEN toLower(n.name) = toLower('{search_text}') THEN 1.0
                    WHEN toLower(n.name) CONTAINS toLower('{search_text}') THEN 0.8
                    WHEN n.alias IS NOT NULL AND toLower(n.alias) CONTAINS toLower('{search_text}') THEN 0.6
                    ELSE 0.4
                END as similarity
            ORDER BY similarity DESC
            LIMIT {limit}
            """
                
            # 执行查询
            result = self.graph.run(cypher_query).data()
            
            # 处理结果
            nodes = []
            for record in result:
                node = record['n']
                similarity = record['similarity']
                
                # 构建返回数据
                node_data = {
                    'id': node.identity,
                    'name': node['name'],
                    'type': list(node.labels)[0] if node.labels else '',
                    'similarity': round(similarity, 2)
                }
                
                # 添加其他属性
                for prop in node:
                    if prop != 'name':  # 名称已添加
                        node_data[prop] = node[prop]
                        
                nodes.append(node_data)
            
            print(f"搜索 '{search_text}' 找到 {len(nodes)} 个匹配节点")
            return {"nodes": nodes, "lines": []}
                
        except Exception as e:
            print(f"节点名称搜索异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"nodes": [], "lines": []}

    def get_default_graph(self, limit=50, load_all=False):
        """
        获取默认图谱数据
        :param limit: 返回的节点数量限制
        :param load_all: 是否加载所有节点和关系，不进行限制
        :return: 包含节点和关系的图谱数据
        """
        try:
            nodes = []
            lines = []
            node_ids = set()
            
            if load_all:
                # 使用一种更可靠的方法保证连通性
                # 1. 先获取所有节点
                node_query = """
                MATCH (n) 
                RETURN n
                """
                node_result = self.graph.run(node_query).data()
                
                # 处理所有节点
                for record in node_result:
                    node = record['n']
                    node_id = node.identity
                    
                    # 添加节点数据
                    node_data = {
                        'id': node_id,
                        'name': node['name'],
                        'type': list(node.labels)[0] if node.labels else ''
                    }
                    
                    # 添加其他属性
                    for prop in node:
                        if prop != 'name':  # 名称已添加
                            node_data[prop] = node[prop]
                    
                    nodes.append(node_data)
                    node_ids.add(node_id)
                
                # 2. 获取所有关系 - 确保使用路径查询而非直接关系查询
                path_query = """
                MATCH path = (n)-[r*1..1]-(m)
                RETURN relationships(path) as rels
                """
                path_result = self.graph.run(path_query).data()
                
                # 添加所有关系
                processed_relations = set()  # 用于去重
                
                for record in path_result:
                    for rel in record['rels']:
                        rel_id = f"{rel.start_node.identity}-{rel.end_node.identity}-{type(rel).__name__}"
                        
                        # 避免重复添加相同关系
                        if rel_id in processed_relations:
                            continue
                            
                        processed_relations.add(rel_id)
                        
                        rel_type = type(rel).__name__
                        
                        # 构建关系数据
                        line_data = {
                            'from': rel.start_node.identity,
                            'to': rel.end_node.identity,
                            'text': rel_type
                        }
                        
                        # 添加关系属性
                        for key, value in rel.items():
                            line_data[key] = value
                            
                        # 特别处理关系类型属性
                        if 'relation_type' in rel:
                            line_data['relation_category'] = rel['relation_type']
                        
                        lines.append(line_data)
                
            else:
                # 原来的有限数据加载逻辑
                node_query = f"""
                MATCH (n)
                RETURN n
                LIMIT {limit}
                """
                
                node_result = self.graph.run(node_query).data()
                
                if not node_result:
                    return {"nodes": [], "lines": []}
                    
                # 处理节点数据
                for record in node_result:
                    node = record['n']
                    node_id = node.identity
                    
                    # 添加节点数据
                    node_data = {
                        'id': node_id,
                        'name': node['name'],
                        'type': list(node.labels)[0] if node.labels else ''
                    }
                    
                    # 添加其他属性
                    for prop in node:
                        if prop != 'name':  # 名称已添加
                            node_data[prop] = node[prop]
                    
                    nodes.append(node_data)
                    node_ids.add(node_id)
                
                # 获取这些节点之间的关系
                if node_ids:
                    # 限制关系数量
                    node_id_list = ", ".join(map(str, node_ids))
                    relation_query = f"""
                    MATCH (n)-[r]-(m)
                    WHERE id(n) IN [{node_id_list}] AND id(m) IN [{node_id_list}]
                    RETURN r
                    LIMIT {limit*2}
                    """
                    relation_result = self.graph.run(relation_query).data()
                    
                    # 处理关系数据
                    for record in relation_result:
                        rel = record['r']
                        rel_type = type(rel).__name__
                        
                        # 构建关系数据
                        line_data = {
                            'from': rel.start_node.identity,
                            'to': rel.end_node.identity,
                            'text': rel_type
                        }
                        
                        # 添加关系属性
                        for key, value in rel.items():
                            line_data[key] = value
                            
                        # 特别处理关系类型属性
                        if 'relation_type' in rel:
                            line_data['relation_category'] = rel['relation_type']
                        
                        lines.append(line_data)
            
            print(f"图谱加载: {len(nodes)}个节点, {len(lines)}个关系, {'加载全部' if load_all else '加载部分'}")
            return {"nodes": nodes, "lines": lines}
            
        except Exception as e:
            print(f"获取默认图谱数据异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"nodes": [], "lines": []}
