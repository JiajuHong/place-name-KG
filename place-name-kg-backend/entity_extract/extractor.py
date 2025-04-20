"""
实体提取器
使用大模型从文本中提取所有地名实体（包括现代地名和历史地名）
"""
import os
import json
import ollama
import time

class Extractor:
    """
    基于大模型的地名实体提取器
    使用Ollama提供的大模型能力和deepseek-r1:7b模型提取所有地名实体
    """
    
    def __init__(self, model_name="deepseek-r1:7b"):
        """初始化提取器"""
        self.model_name = model_name
        print(f"已初始化大模型地名实体提取器，使用模型: {model_name}")
    
    def extract_entities(self, text):
        """
        从文本中提取所有地名实体（包括现代地名和历史地名）
        
        Args:
            text: 输入文本
            
        Returns:
            list: 提取的地名实体列表
        """
        if not text or len(text.strip()) == 0:
            print("输入文本为空，无法提取实体")
            return []
        
        # 记录文本的开头部分作为示例
        text_preview = text[:100] + "..." if len(text) > 100 else text
        print(f"准备提取文本中的地名实体，文本长度: {len(text)} 字符，文本开头: '{text_preview}'")
        
        # 构建提示词
        prompt = self._build_prompt(text)
        
        try:
            # 记录总体开始时间
            total_start_time = time.time()
            
            # 记录模型调用开始时间
            model_start_time = time.time()
            print(f"调用 {self.model_name} 模型进行地名实体提取...")
            # 调用大模型进行实体提取
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的地名识别专家。你的任务是从文本中准确识别出所有地名实体，"
                                   "包括现代和历史地名、国内和国外地名、行政区划、自然地理实体等。请返回所有可能的地名，"
                                   "不要遗漏任何地名。返回的地名实体应当是具体的地点名称，而不是泛指的地理概念。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                stream=False
            )
            
            # 记录模型调用耗时
            model_time = time.time() - model_start_time
            print(f"模型响应成功，耗时: {model_time:.2f}秒，"
                  f"响应长度: {len(response['message']['content'])} 字符，开始解析实体...")
            
            # 记录解析开始时间
            parse_start_time = time.time()
            
            # 从响应中解析实体
            extracted_entities = self._parse_entities_from_response(response['message']['content'])
            
            # 记录解析耗时
            parse_time = time.time() - parse_start_time
            
            # 如果解析到了实体，记录一些示例
            if extracted_entities:
                entity_examples = ', '.join(extracted_entities[:5])
                entity_examples += "..." if len(extracted_entities) > 5 else ""
                print(f"解析得到 {len(extracted_entities)} 个初步实体，解析耗时: {parse_time:.2f}秒，示例: {entity_examples}")
            else:
                print(f"解析完成但未找到任何实体，解析耗时: {parse_time:.2f}秒，请检查文本内容或模型响应")
            
            # 记录后处理开始时间
            postprocess_start_time = time.time()
            
            # 过滤和排序结果
            result = self._post_process_entities(extracted_entities)
            
            # 记录后处理耗时
            postprocess_time = time.time() - postprocess_start_time
            
            # 计算总体耗时
            total_time = time.time() - total_start_time
            
            # 记录详细的性能统计
            print(f"地名实体提取完成，总耗时: {total_time:.2f}秒")
            print(f"性能指标 - 模型调用: {model_time:.2f}秒 ({model_time/total_time:.1%}), 解析: {parse_time:.2f}秒 ({parse_time/total_time:.1%}), 后处理: {postprocess_time:.2f}秒 ({postprocess_time/total_time:.1%})")
            
            # 记录结果统计信息
            if result:
                result_examples = ', '.join(result[:5])
                result_examples += "..." if len(result) > 5 else ""
                avg_entity_length = sum(len(entity) for entity in result) / max(1, len(result))
                print(f"实体统计 - 初始解析: {len(extracted_entities)}个, 最终有效: {len(result)}个, 过滤率: {(1 - len(result)/max(1, len(extracted_entities))):.2%}")
                print(f"实体质量 - 平均长度: {avg_entity_length:.1f}字符, 最终实体示例: {result_examples}")
                print(f"提取比率 - 每千字符实体数: {(len(result) * 1000 / max(1, len(text))):.2f}")
            else:
                print(f"警告: 后处理后没有剩余有效实体，请检查过滤条件或原始提取结果")
            
            return result
            
        except Exception as e:
            error_type = type(e).__name__
            error_details = str(e)
            print(f"大模型实体提取失败: {error_type} - {error_details}")
            import traceback
            print(f"错误追踪: {traceback.format_exc()}")
            # 如果大模型调用失败，返回空列表
            return []
    
    def _build_prompt(self, text):
        """构建提示词，引导模型提取所有地名实体"""
        prompt = f"""请从以下文本中识别并提取所有地名实体:

{text}

要求:
1. 提取所有地名实体，包括现代地名和历史地名
2. 包括城市、省份、国家、地区、山川、河流等所有地理实体
3. 包括现代行政区划（如市、区、县）和古代行政区划（如府、州、郡、县、路）
4. 尽可能详尽地提取所有地名，不要遗漏
5. 专注于识别"地名"，不要提取人名、组织名称等其他实体类型

请以JSON格式返回提取结果，格式如下:
```json
{{
  "entities": ["地名1", "地名2", "地名3", ...]
}}
```

只返回JSON结果，不要有其他解释。"""
        
        return prompt
    
    def _parse_entities_from_response(self, response_text):
        """从模型响应中解析实体列表"""
        try:
            # 尝试从响应中提取JSON部分
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                try:
                    data = json.loads(json_str)
                    if 'entities' in data and isinstance(data['entities'], list):
                        print(f"成功通过JSON格式解析，找到实体数量: {len(data['entities'])}")
                        return data['entities']
                except Exception as json_err:
                    print(f"JSON解析失败: {str(json_err)}")
            
            # 如果没找到JSON或解析失败，尝试其他解析方法
            # 查找列表形式
            if '[' in response_text and ']' in response_text:
                list_start = response_text.find('[')
                list_end = response_text.rfind(']') + 1
                if list_start >= 0 and list_end > list_start:
                    list_str = response_text[list_start:list_end]
                    try:
                        entities = json.loads(list_str)
                        if isinstance(entities, list):
                            print(f"通过列表格式解析，找到实体数量: {len(entities)}")
                            return entities
                    except Exception as list_err:
                        print(f"列表解析失败: {str(list_err)}")
            
            print("标准解析失败，尝试按行分割进行解析")
            # 回退方案：按行分割并清理
            lines = response_text.split('\n')
            entities = []
            for line in lines:
                line = line.strip()
                # 移除行首的数字、点、破折号等前缀
                line = line.lstrip('0123456789.- "\'')
                line = line.strip()
                if line and len(line) >= 2:
                    entities.append(line)
            
            print(f"通过行分割解析，找到实体数量: {len(entities)}")
            return entities
            
        except Exception as e:
            print(f"解析模型响应失败: {str(e)}")
            print(f"原始响应: {response_text}")
            return []
    
    def _post_process_entities(self, entities):
        """对提取的实体进行后处理，包括去重、过滤和排序"""
        if not entities:
            return []
        
        # 去重
        unique_entities = list(set(entities))
        print(f"实体去重: {len(entities)} -> {len(unique_entities)}个")
        
        # 过滤明显不是地名的实体和太短的实体
        filtered_entities = [entity for entity in unique_entities 
                            if len(entity) >= 2 and not self._should_filter(entity)]
        
        print(f"实体过滤: {len(unique_entities)} -> {len(filtered_entities)}个")
        if len(unique_entities) > len(filtered_entities):
            filtered_out = set(unique_entities) - set(filtered_entities)
            print(f"被过滤掉的实体: {', '.join(filtered_out)}")
        
        # 按长度排序（优先考虑较长的地名，通常更具体）
        filtered_entities.sort(key=len, reverse=True)
        
        # 返回所有有效实体，不限制数量
        return filtered_entities
    
    def _should_filter(self, entity):
        """检查实体是否应该被过滤"""
        # 过滤常见的非地名词汇
        non_place_words = [
            # 疑问词
            "什么", "哪些", "如何", "为何", "为什么", "怎么", "怎样", "哪里", "谁", "何时", "多少", 
            # 常见动词
            "怎么样", "是什么", "有什么", "有哪些", "怎么办", "属于", "位于", 
            # 泛指地理概念
            "关系", "地区", "地方", "位置", "地点", "区域", "城市", "省份", "国家", "行政区划",
            "县城", "地界", "郡县", "古代", "现代", "山川", "河流"
        ]
        
        # 检查是否是非地名词汇
        if entity in non_place_words:
            return True
        
        # 过滤纯数字
        if entity.isdigit():
            return True
        
        # 过滤只有一个字符的实体
        if len(entity) <= 1:
            return True
        
        return False 