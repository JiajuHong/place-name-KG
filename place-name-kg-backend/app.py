import json
import os
import time
import uuid

from flask import Flask, request, jsonify, g
from flask_cors import CORS

from db_utils import DbUtil
from jwt_util import decode, encode
from model_search import neo4j_db

app = Flask(__name__)
CORS(app)  # 允许所有域名访问
neo4j_db_handle = neo4j_db()
user_id = None

# 获取项目目录
APP_PATH = os.path.dirname(__file__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{APP_PATH}/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
DbUtil.init_app(app)

# 历史地名词典
historical_places = []

# 修复：替换不再支持的before_first_request装饰器
@app.before_request
def initialize_entity_extractor():
    # 添加对entity_extract的支持
    if not hasattr(g, 'entity_extractor'):
        try:
            from entity_extract.extractor import Extractor
            g.entity_extractor = Extractor()
            print("实体提取器已初始化")
        except Exception as e:
            print(f"初始化实体提取器失败: {str(e)}")
            
    # 添加对规则推理模块的支持
    if not hasattr(g, 'rule_llm_integration'):
        try:
            from inference.rule_llm_integration import RuleLLMIntegration
            g.rule_llm_integration = RuleLLMIntegration(
                rule_file_path='rules/rule_base.json',
                model_name='deepseek-r1:7b',
                max_depth=30
            )
            print("规则推理模块已初始化")
        except Exception as e:
            print(f"初始化规则推理模块失败: {str(e)}")



# 初始化用户词典
def init_user_dict():
    """从data.json提取地名实体并创建历史地名词典文件"""
    dict_path = os.path.join(APP_PATH, 'historical_places.txt')
    data_json_path = os.path.join(APP_PATH, 'data', 'data.json')
    
    try:
        # 检查data.json是否存在
        if not os.path.exists(data_json_path):
            print(f"警告：data.json文件不存在: {data_json_path}")
            return
        
        # 读取data.json文件
        with open(data_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"从data.json中提取实体，共有{len(data)}条记录")
        
        # 提取所有实体名称、类型和关系
        entities = set()  # 实体名称
        entity_types = set()  # 实体类型
        relation_types = set()  # 关系类型
        
        for item in data:
            # 提取实体名称
            if "实体名称" in item and item["实体名称"]:
                entities.add(item["实体名称"])
            
            # 提取关联实体
            if "关联实体" in item and item["关联实体"]:
                # 处理可能包含多个实体的情况（如：长洲县、元和县）
                associated_entities = item["关联实体"].split("、")
                for entity in associated_entities:
                    entities.add(entity)
            
            # 提取实体类型
            if "实体类型" in item and item["实体类型"]:
                entity_types.add(item["实体类型"])
            
            # 提取关联实体类型
            if "关联实体类型" in item and item["关联实体类型"]:
                entity_types.add(item["关联实体类型"])
            
            # 提取关系类型
            if "实体关系" in item and item["实体关系"]:
                relation_types.add(item["实体关系"])
        
        # 添加朝代和时间单位
        dynasties = [
            "秦朝", "汉朝", "西汉", "东汉", "三国", "魏国", "蜀国", "吴国",
            "晋朝", "西晋", "东晋", "南北朝", "隋朝", "唐朝", "五代十国", 
            "宋朝", "北宋", "南宋", "辽朝", "金朝", "元朝", "明朝", "清朝", "民国"
        ]
        
        for dynasty in dynasties:
            entities.add(dynasty)
        
        # 组装词典内容
        # 格式：词语 频率 词性
        dict_content = []
        
        # 添加实体名称，标记为地名 (ns)
        for entity in entities:
            dict_content.append(f"{entity} 10 ns")
        
        # 添加实体类型，标记为名词 (n)
        for entity_type in entity_types:
            dict_content.append(f"{entity_type} 10 n")
        
        # 添加关系类型，标记为动词 (v)
        for relation in relation_types:
            dict_content.append(f"{relation} 10 v")
        
        # 写入文件
        with open(dict_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(dict_content))
        
        print(f"已成功生成历史地名词典文件: {dict_path}")
        print(f"词典包含 {len(entities)} 个实体名称, {len(entity_types)} 个实体类型, {len(relation_types)} 个关系类型")
        
    except Exception as e:
        print(f"创建历史地名词典文件失败: {str(e)}")
        import traceback
        traceback.print_exc()

# 调用初始化函数
init_user_dict()

# 预加载jieba分词用户词典
try:
    import jieba
    
    dict_path = os.path.join(APP_PATH, 'historical_places.txt')
    if os.path.exists(dict_path):
        jieba.load_userdict(dict_path)
        print(f"成功加载历史地名词典: {dict_path}")
    else:
        print(f"警告：历史地名词典不存在: {dict_path}")
except ImportError:
    print("未找到jieba分词库，跳过用户词典加载")
except Exception as e:
    print(f"加载用户词典失败: {str(e)}")


@app.before_request
def before():
    url = request.path  # 当前请求的URL
    print('url:' + url)
    pass_url = ["/", "/api/login", "/api/sign_in"]
    if url.startswith("/static") or url in pass_url:
        pass
    else:
        token = request.headers.get('Token')
        if not token:
            return jsonify({
                "code": 403,
                "msg": "您还未登录，请先登录"
            })
        else:
            global user_id
            user_id = decode(token)['user_id']


@app.route('/api/login', methods=['POST'])
def login():
    global user_id
    params = request.get_json()
    handler = DbUtil()
    user = handler.authentication(params)
    if user:
        token = encode(user.id)
        return jsonify({
            "code": 200,
            "data": token
        })
    else:
        return jsonify({
            "code": 403,
            "msg": "用户名或密码错误"
        })


# 查询用户信息
@app.route('/api/userinfo', methods=['GET', 'POST'])
def userinfo():
    handler = DbUtil()
    global user_id
    result = handler.find_user(user_id)
    return jsonify({
        "code": 200,
        "data": result
    })


@app.route('/api/sign_in', methods=['POST'])
def sign_in():
    """
    注册
    """
    data = request.get_json()
    handler = DbUtil()
    return handler.add_user(data)


@app.route('/search_name_kg', methods=['POST'])
def search_name():
    """
    搜索地名知识图谱
    """
    data = request.get_json()
    entity = data.get('name', '')
    node_type = data.get('node_type', '')
    rel_type = data.get('rel_type', '')
    load_all = data.get('load_all', True)  # 默认加载所有节点和关系
    
    try:
        # 如果没有提供任何参数，则使用默认图谱加载并加载所有关系
        if not entity and not node_type and not rel_type:
            json_data = neo4j_db_handle.get_default_graph(limit=50, load_all=load_all)
            print(f"使用默认图谱加载方式, {'加载全部' if load_all else '加载部分'}")
        else:
            # 根据提供的不同参数类型，使用不同的专用函数
            if entity:
                # 使用实体名称搜索
                json_data = neo4j_db_handle.search_nodes_by_name(entity)
                print(f"按实体名称'{entity}'搜索")
            elif node_type:
                # 按节点类型筛选
                json_data = neo4j_db_handle.get_nodes_by_type(node_type)
                print(f"按节点类型'{node_type}'筛选")
            elif rel_type:
                # 按关系类型筛选
                json_data = neo4j_db_handle.get_nodes_by_relationship(rel_type)
                print(f"按关系类型'{rel_type}'筛选")
            
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": json_data
        })
    except Exception as e:
        print(f"搜索地名知识图谱异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "code": 500,
            "msg": str(e),
            "data": {"nodes": [], "lines": []}
        })


@app.route('/api/find_node_page', methods=['POST'])
def find_list():
    # 获取前端传递的参数
    current = int(request.json.get('pageNum', 1))
    limit = int(request.json.get('pageSize', 10))
    name_query = request.json.get('name', '')
    json_data = neo4j_db_handle.find_node_page(current, limit, name_query)
    return jsonify({
        "code": 200,
        "data": json_data
    })


@app.route('/create_node', methods=['POST'])
def create_node():
    data = request.json
    node = neo4j_db_handle.create_node(data.get("type"), data.get("name"))
    return jsonify({
        "code": 200,
        "data": node
    })


@app.route('/update_node', methods=['POST'])
def update_node():
    data = request.json
    node = neo4j_db_handle.update_node(data.get("type"), data.get("id"), data.get("name"))
    return jsonify({
        "code": 200,
        "data": node
    })


@app.route('/delete_node', methods=['POST'])
def delete_node():
    data = request.json
    node = neo4j_db_handle.delete_node(data.get("type"), data.get("id"))
    return jsonify({
        "code": 200,
        "data": node
    })



@app.route('/api/node_types', methods=['GET'])
def get_node_types():
    """获取所有节点类型"""
    try:
        types = neo4j_db_handle.get_node_types()
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": types
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e)
        })


@app.route('/api/relationship_types', methods=['GET'])
def get_relationship_types():
    """获取所有关系类型"""
    try:
        types = neo4j_db_handle.get_relationship_types()
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": types
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e)
        })


@app.route('/api/node/detail', methods=['GET'])
def get_node_detail():
    """获取节点的详细属性"""
    try:
        node_id = request.args.get('id')
        if not node_id:
            return jsonify({
                "code": 400,
                "msg": "节点ID不能为空"
            })
        
        node_detail = neo4j_db_handle.get_node_detail(node_id)
        if not node_detail:
            return jsonify({
                "code": 404,
                "msg": "节点不存在"
            })
            
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": node_detail
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e)
        })


@app.route('/api/node/update_properties', methods=['POST'])
def update_node_properties():
    """更新节点的所有属性"""
    try:
        data = request.json
        node_id = data.get("id")
        properties = data.get("properties")
        
        if not node_id:
            return jsonify({
                "code": 400,
                "msg": "节点ID不能为空"
            })
            
        if not properties or not isinstance(properties, dict):
            return jsonify({
                "code": 400,
                "msg": "节点属性格式不正确"
            })
            
        success = neo4j_db_handle.update_node_properties(node_id, properties)
        if not success:
            return jsonify({
                "code": 404,
                "msg": "节点不存在或更新失败"
            })
            
        return jsonify({
            "code": 200,
            "msg": "success"
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e)
        })


@app.route('/api/node/relations', methods=['GET'])
def get_node_relations():
    """获取节点的所有直接关系"""
    try:
        node_id = request.args.get('id')
        if not node_id:
            return jsonify({
                "code": 400,
                "msg": "节点ID不能为空"
            })
        
        result = neo4j_db_handle.get_node_relations(node_id)
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e)
        })


@app.route('/api/node/by_type', methods=['GET'])
def get_nodes_by_type():
    """根据节点类型获取节点列表"""
    try:
        node_type = request.args.get('type')
        if not node_type:
            return jsonify({
                "code": 400,
                "msg": "节点类型不能为空"
            })
        
        result = neo4j_db_handle.get_nodes_by_type(node_type)
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e)
        })


@app.route('/api/node/by_relationship', methods=['GET'])
def get_nodes_by_relationship():
    """按关系类型获取节点"""
    try:
        rel_type = request.args.get('type')
        if not rel_type:
            return jsonify({
                "code": 400,
                "msg": "关系类型不能为空"
            })
        
        result = neo4j_db_handle.get_nodes_by_relationship(rel_type)
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e)
        })


@app.route('/api/node/search_by_name', methods=['GET'])
def search_nodes_by_name():
    """按节点名称进行模糊搜索"""
    try:
        search_text = request.args.get('name')
        limit = request.args.get('limit', 100, type=int)
        
        if not search_text:
            return jsonify({
                "code": 400,
                "msg": "搜索文本不能为空"
            })
        
        result = neo4j_db_handle.search_nodes_by_name(search_text, limit)
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e)
        })


@app.route('/api/ai/inference', methods=['POST', 'GET'])
def ai_inference():
    """使用大模型进行推理"""
    try:
        # 获取请求参数
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '请求参数不能为空'
                }), 400
            
            user_question = data.get('question', '')
        else:  # GET请求
            user_question = request.args.get('question', '')
        
        # 验证问题不为空
        if not user_question or len(user_question.strip()) == 0:
            return jsonify({
                'success': False,
                'error': '问题不能为空'
            }), 400
        
        # 请求ID用于日志跟踪
        request_id = str(uuid.uuid4())[:8]
        print(f"[{request_id}] 收到大模型推理请求: '{user_question}'")
        
        # 确保推理引擎已初始化
        if not hasattr(g, 'rule_llm_integration'):
            # 初始化推理引擎
            print(f"[{request_id}] 初始化规则推理模块")
            try:
                from inference.rule_llm_integration import RuleLLMIntegration
                g.rule_llm_integration = RuleLLMIntegration(
                    rule_file_path='rules/rule_base.json',
                    model_name='deepseek-r1:7b',
                    max_depth=3
                )
            except Exception as init_err:
                print(f"[{request_id}] 初始化规则推理模块失败: {str(init_err)}")
                return jsonify({
                    'success': False,
                    'error': '系统初始化失败，请稍后再试',
                    'answer': '抱歉，推理系统正在初始化中，请稍后再试。',
                    'kg_data': {'nodes': [], 'lines': []}
                }), 500
        
        # 确保实体提取器已初始化
        if not hasattr(g, 'entity_extractor'):
            print(f"[{request_id}] 初始化实体提取器")
            try:
                from entity_extract.extractor import Extractor
                g.entity_extractor = Extractor()
            except Exception as init_err:
                print(f"[{request_id}] 初始化实体提取器失败: {str(init_err)}")
                return jsonify({
                    'success': False,
                    'error': '实体提取器初始化失败，请稍后再试',
                    'answer': '抱歉，地名识别系统正在初始化中，请稍后再试。',
                    'kg_data': {'nodes': [], 'lines': []}
                }), 500
        
        # 处理用户问题
        print(f"[{request_id}] 开始处理问题...")
        start_time = time.time()
        
        try:
            result = g.rule_llm_integration.process_question(
                question=user_question,
                entity_extractor=g.entity_extractor,
                neo4j_db=neo4j_db_handle
            )
            
            # 构建响应
            process_time = result.get('process_time', 0)
            entities = result.get('entities', [])
            
            # 记录处理结果
            print(f"[{request_id}] 问题处理完成，耗时: {process_time:.2f}秒, 识别到 {len(entities)} 个实体")
            if entities:
                print(f"[{request_id}] 识别到的实体: {', '.join(entities[:5])}" + ("..." if len(entities) > 5 else ""))
            
            # 检查知识图谱数据
            kg_data = result.get('kg_data', {'nodes': [], 'lines': []})
            node_count = len(kg_data.get('nodes', []))
            line_count = len(kg_data.get('lines', []))
            print(f"[{request_id}] 生成的知识图谱数据: {node_count} 个节点, {line_count} 条关系")
            
            # 获取格式化的关系文本
            relations_text = result.get('context', '未找到相关关系数据')
            
            # 返回完整响应
            response = {
                'success': True,
                'answer': result.get('answer', '抱歉，无法回答这个问题'),
                'kg_data': kg_data,
                'entities': entities,
                'process_time': process_time,
                'relations_text': relations_text  # 添加格式化的关系文本
            }
            
            return jsonify(response)
            
        except Exception as process_err:
            error_type = type(process_err).__name__
            error_msg = str(process_err)
            
            print(f"[{request_id}] 处理问题时出错: {error_type} - {error_msg}")
            import traceback
            traceback.print_exc()
            
            # 根据错误类型提供不同的用户友好错误信息
            user_message = "抱歉，处理您的问题时遇到了技术问题。"
            
            if "ConnectionRefused" in error_type or "ConnectionError" in error_type:
                user_message = "抱歉，无法连接到知识库服务器，请检查数据库连接。"
            elif "TimeoutError" in error_type:
                user_message = "抱歉，查询超时，请尝试简化您的问题或稍后再试。"
            elif "ollama" in error_msg.lower():
                user_message = "抱歉，大模型服务暂时不可用，请稍后再试。"
            elif "memory" in error_msg.lower() or "cuda" in error_msg.lower():
                user_message = "抱歉，系统资源不足，请稍后再试。"
            elif "invalid" in error_msg.lower() or "syntax" in error_msg.lower():
                user_message = "抱歉，您的问题格式可能有误，请尝试用不同方式提问。"
            
            return jsonify({
                'success': False,
                'error': f'处理问题时出错: {error_type}',
                'error_detail': error_msg,
                'answer': user_message,
                'kg_data': {'nodes': [], 'lines': []},
                'process_time': time.time() - start_time
            }), 500
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"处理推理请求时出错: {error_type} - {error_msg}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'请求处理错误: {error_type}',
            'error_detail': error_msg,
            'answer': f"抱歉，系统无法处理您的请求。请检查输入格式是否正确，或稍后再试。",
            'kg_data': {'nodes': [], 'lines': []}
        }), 500


@app.route('/user/menu', methods=['GET'])
def get_menu():
    """获取系统菜单"""
    menu_data = [
        {
            "id": "/knowledge",
            "icon": "layui-icon-set",
            "title": "知识图谱",
            "children": [
                {
                    "id": "/knowledge/graph",
                    "icon": "layui-icon-find-fill",
                    "title": "知识图谱可视化"
                },
                {
                    "id": "/knowledge-list",
                    "icon": "layui-icon-fonts-code",
                    "title": "知识节点管理"
                },
                {
                    "id": "/knowledge/inference",
                    "icon": "layui-icon-engine",
                    "title": "大模型推理"
                }
            ]
        }
    ]
    
    return jsonify({
        "code": 200,
        "data": menu_data
    })

# 移除条件检查，确保应用始终在所有网络接口上监听
# 这样在PyCharm和命令行中都能正常工作
if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')
