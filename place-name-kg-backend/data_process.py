import json
import os
from datetime import datetime
from py2neo import Graph, Node, Relationship

# 连接到Neo4j数据库
graph = Graph("bolt://localhost:7687", auth=("neo4j", "123456"))


def read_json_files(directory):
    """
    读取指定目录下的所有JSON文件
    参数:
        directory (str): 要搜索的目录路径
    返回:
        list: 包含所有JSON文件内容的列表
    """
    json_data = []
    # 遍历目录下的所有文件
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            try:
                # 读取并解析JSON文件
                with open(filepath, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    json_data.append(data)
            except json.JSONDecodeError as e:
                print(f"解析文件 {filename} 时出错: {e}")
            except Exception as e:
                print(f"读取文件 {filename} 时发生错误: {e}")

    return json_data


def get_attributes(address_attributes, address):
    """
    获取地址属性
    """
    for address_attribute in address_attributes:
        if address_attribute.get("中文名") == address:
            return address_attribute
    return None


def is_evolution_relation(relation):
    """
    判断是否为沿革关系
    """
    evolution_keywords = [
        '沿革', '撤', '设', '改', '更名', '改名', '更', 
        '改设', '改置', '改称', '设立', '升格', '变更'
    ]
    return any(keyword in relation for keyword in evolution_keywords)


def format_relation(relation, date):
    """
    格式化关系名称
    """
    if not date:
        return relation
    # 如果关系已经包含时间，直接返回关系
    if date in relation:
        return relation
    # 否则添加时间前缀
    return f"{date}_{relation}"


def get_time_from_name(name):
    """
    从名称中提取时间
    """
    import re
    match = re.search(r'(\d{4})', name)
    return int(match.group(1)) if match else None


def save_to_neo(data, address_attributes):
    """
    保存数据到Neo4j
    """
    # 获取基本数据
    label1 = data.get("实体类型")
    entity1 = data.get("实体名称")
    relation = data.get("实体关系")
    label2 = data.get("关联实体类型")
    entity2 = data.get("关联实体")
    date = data.get("时间", "")
    relation_type = data.get("关系类型", "")  # 新增字段：关系类型

    # 验证必要字段
    if not all([label1, entity1, relation, label2, entity2]):
        print(f"数据不完整: {data}")
        return

    # 创建或获取实体节点
    node1 = graph.nodes.match(name=entity1).first()
    if not node1:
        node1_attributes = get_attributes(address_attributes, entity1)
        if node1_attributes:
            node1 = Node(label1, name=entity1, **node1_attributes)
        else:
            node1 = Node(label1, name=entity1)
        graph.create(node1)

    # 处理目标实体（支持多个）
    target_entities = entity2.split("、") if "、" in entity2 else entity2.split(",")
    
    for target_entity in target_entities:
        try:
            # 创建或获取目标节点
            node2 = graph.nodes.match(name=target_entity).first()
            if not node2:
                node2_attributes = get_attributes(address_attributes, target_entity)
                if node2_attributes:
                    node2 = Node(label2, name=target_entity, **node2_attributes)
                else:
                    node2 = Node(label2, name=target_entity)
                graph.merge(node2, label2, "name")

            # 格式化关系名称
            formatted_relation = format_relation(relation, date)
            
            # 如果是"演变类"关系，则反转关系方向
            if relation_type == "演变类":
                # 反转关系方向：关联实体 -> 实体名称
                rel = Relationship(node2, formatted_relation, node1)
            else:
                # 保持原有方向：实体名称 -> 关联实体
                rel = Relationship(node1, formatted_relation, node2)

            # 添加时间属性
            if date:
                rel['time'] = date
                
            # 添加关系类型属性
            if relation_type:
                rel['relation_type'] = relation_type
                
            # 创建关系
            graph.create(rel)
            
        except Exception as e:
            print(f"处理关系时出错: {data}, 错误: {e}")


def main():
    # 清空数据库
    graph.delete_all()
    
    # 读取属性数据
    address_attributes = read_json_files("result")
    
    # 读取并处理主数据
    with open('data/data.json', 'r', encoding='utf-8') as file:
    # with open('data/data1.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        for item in data:
            try:
                save_to_neo(item, address_attributes)
            except Exception as e:
                print(f"处理数据时出错: {item}, 错误: {e}")


if __name__ == '__main__':
    main()
