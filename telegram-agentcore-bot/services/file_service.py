"""
檔案處理服務
使用 AgentCore Code Interpreter 處理檔案
"""
import os
import boto3
import base64
from typing import Dict, Any, Optional
from utils.logger import get_logger
from utils.audit import audit_log
from config.settings import settings

logger = get_logger(__name__)

# S3 客戶端（延遲初始化）
_s3_client = None

def get_s3_client():
    """獲取 S3 客戶端單例"""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


class FileService:
    """檔案處理服務類"""
    
    def __init__(self, region: str):
        """
        初始化檔案服務
        
        Args:
            region: AWS 區域
        """
        self.region = region
        self.enabled = settings.FILE_ENABLED
        self.bucket = settings.FILE_STORAGE_BUCKET
        self.client = None
        
        if self.enabled:
            self._initialize_client()
        else:
            logger.info("📁 檔案處理功能未啟用")
    
    def _initialize_client(self):
        """初始化 Code Interpreter 客戶端"""
        try:
            from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
            
            self.CodeInterpreter = CodeInterpreter
            logger.info("✅ File Service 初始化成功")
            
        except ImportError as e:
            logger.error(f"❌ Code Interpreter 匯入失敗: {str(e)}")
            self.enabled = False
    
    def is_available(self) -> bool:
        """檢查服務是否可用"""
        return self.enabled and self.bucket != ''
    
    def read_from_s3(self, s3_url: str) -> Optional[bytes]:
        """
        從 S3 讀取檔案
        
        Args:
            s3_url: S3 URL (格式: s3://bucket/key)
        
        Returns:
            檔案內容（bytes）或 None
        """
        try:
            # 解析 S3 URL
            if not s3_url.startswith('s3://'):
                logger.error(f"Invalid S3 URL: {s3_url}")
                return None
            
            # 移除 s3:// 前綴
            url_parts = s3_url[5:].split('/', 1)
            if len(url_parts) != 2:
                logger.error(f"Invalid S3 URL format: {s3_url}")
                return None
            
            bucket, key = url_parts
            
            # 從 S3 讀取
            s3_client = get_s3_client()
            response = s3_client.get_object(Bucket=bucket, Key=key)
            file_content = response['Body'].read()
            
            logger.info(
                f"✅ Read from S3: {len(file_content)} bytes",
                extra={
                    'event_type': 's3_read_success',
                    'bucket': bucket,
                    'key': key,
                    'size': len(file_content)
                }
            )
            
            return file_content
            
        except Exception as e:
            logger.error(
                f"❌ Failed to read from S3: {str(e)}",
                extra={
                    'event_type': 's3_read_failure',
                    's3_url': s3_url
                },
                exc_info=True
            )
            return None
    
    def process_file(
        self, 
        s3_url: str,
        filename: str,
        task: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        處理檔案
        
        Args:
            s3_url: S3 URL
            filename: 檔案名稱
            task: 處理任務描述
            user_id: 用戶 ID（用於審計）
        
        Returns:
            處理結果字典
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "檔案處理功能未啟用或未配置 S3 bucket"
            }
        
        session_id = None
        
        try:
            # 審計：記錄檔案處理開始
            audit_log(
                user_id=user_id,
                action="FILE_PROCESS_START",
                resource=filename,
                details={"task": task, "s3_url": s3_url}
            )
            
            # 1. 從 S3 讀取檔案
            file_content = self.read_from_s3(s3_url)
            if not file_content:
                return {
                    "success": False,
                    "error": "無法從 S3 讀取檔案"
                }
            
            logger.info(f"📁 開始處理檔案: {filename} ({len(file_content)} bytes)")
            
            # 2. 啟動 Code Interpreter session
            client = self.CodeInterpreter(self.region)
            client.start()
            session_id = client.session_id
            logger.info(f"✅ Code Interpreter session 已啟動: {session_id}")
            
            # 3. 上傳檔案到 session
            file_text = self._prepare_file_content(file_content, filename)
            
            write_response = client.invoke("writeFiles", {
                "content": [{
                    "path": filename,
                    "text": file_text
                }]
            })
            
            logger.info(f"✅ 檔案已上傳到 session: {filename}")
            
            # 4. 根據任務類型處理檔案
            result = self._execute_task(client, filename, task)
            
            # 5. 停止 session
            client.stop()
            session_id = None
            logger.info("✅ Session 已清理")
            
            # 審計：記錄處理成功
            audit_log(
                user_id=user_id,
                action="FILE_PROCESS_SUCCESS",
                resource=filename,
                details={"task": task, "result_length": len(str(result))}
            )
            
            return {
                "success": True,
                "result": result,
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"❌ 檔案處理錯誤: {str(e)}", exc_info=True)
            
            # 審計：記錄處理失敗
            audit_log(
                user_id=user_id,
                action="FILE_PROCESS_FAILURE",
                resource=filename,
                details={"task": task, "error": str(e)}
            )
            
            return {
                "success": False,
                "error": f"處理失敗: {str(e)}"
            }
            
        finally:
            # 確保 session 被清理
            if session_id and self.client:
                try:
                    self.client.stop()
                    logger.info(f"✅ Session 清理完成: {session_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Session 清理失敗: {str(e)}")
    
    def _prepare_file_content(self, content: bytes, filename: str) -> str:
        """
        準備檔案內容（轉換為文字）
        
        Args:
            content: 檔案內容（bytes）
            filename: 檔案名稱
        
        Returns:
            文字格式的檔案內容
        """
        # 嘗試解碼為 UTF-8
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            # 如果是二進位檔案，使用 base64 編碼
            logger.info(f"檔案 {filename} 為二進位格式，使用 base64 編碼")
            return base64.b64encode(content).decode('ascii')
    
    def _execute_task(self, client, filename: str, task: str) -> str:
        """
        執行處理任務
        
        Args:
            client: Code Interpreter 客戶端
            filename: 檔案名稱
            task: 任務描述
        
        Returns:
            處理結果文字
        """
        # 根據任務類型生成不同的處理程式碼
        if "摘要" in task or "summary" in task.lower():
            code = self._generate_summary_code(filename)
        elif "分析" in task or "analyze" in task.lower():
            code = self._generate_analysis_code(filename)
        elif "統計" in task or "statistics" in task.lower():
            code = self._generate_statistics_code(filename)
        else:
            # 預設：摘要
            code = self._generate_summary_code(filename)
        
        logger.info(f"執行任務: {task}")
        
        # 執行程式碼
        response = client.invoke("executeCode", {
            "code": code,
            "language": "python",
            "clearContext": False
        })
        
        # 提取結果
        result = self._extract_result(response)
        return result
    
    def _generate_summary_code(self, filename: str) -> str:
        """生成摘要程式碼"""
        return f"""
import os

# 讀取檔案
with open('{filename}', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\\n')

# 生成摘要
print("📄 檔案摘要")
print(f"檔案名稱: {filename}")
print(f"總行數: {{len(lines)}}")
print(f"總字元數: {{len(content)}}")
print(f"檔案大小: {{os.path.getsize('{filename}')}} bytes")
print()

# 顯示前 15 行內容
print("📝 前 15 行內容:")
for i, line in enumerate(lines[:15], 1):
    # 限制每行最多顯示 100 字元
    display_line = line[:100] + "..." if len(line) > 100 else line
    print(f"{{i:2d}}. {{display_line}}")

if len(lines) > 15:
    print(f"\\n... (省略 {{len(lines) - 15}} 行)")
"""
    
    def _generate_analysis_code(self, filename: str) -> str:
        """生成分析程式碼（針對 CSV/JSON）"""
        return f"""
import os
import json

# 判斷檔案類型
file_ext = os.path.splitext('{filename}')[1].lower()

print(f"📊 檔案分析: {filename}")
print(f"檔案類型: {{file_ext}}")
print()

if file_ext == '.csv':
    import csv
    with open('{filename}', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        print(f"✅ CSV 檔案分析")
        print(f"總行數: {{len(rows)}}")
        
        if rows:
            print(f"\\n欄位清單:")
            for i, col in enumerate(rows[0].keys(), 1):
                print(f"  {{i}}. {{col}}")
            
            print(f"\\n前 5 筆資料:")
            for i, row in enumerate(rows[:5], 1):
                print(f"\\n第 {{i}} 筆:")
                for key, value in row.items():
                    display_value = str(value)[:50] + "..." if len(str(value)) > 50 else value
                    print(f"  - {{key}}: {{display_value}}")
            
            if len(rows) > 5:
                print(f"\\n... (省略 {{len(rows) - 5}} 筆資料)")
            
elif file_ext == '.json':
    with open('{filename}', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        print(f"✅ JSON 檔案分析")
        print(f"資料類型: {{type(data).__name__}}")
        
        if isinstance(data, list):
            print(f"元素數量: {{len(data)}}")
            if data:
                print(f"\\n第一個元素:")
                print(json.dumps(data[0], indent=2, ensure_ascii=False)[:500])
                
        elif isinstance(data, dict):
            print(f"\\n主要鍵值:")
            for i, (key, value) in enumerate(list(data.items())[:10], 1):
                value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"  {{i}}. {{key}}: {{value_str}}")
            
            if len(data) > 10:
                print(f"\\n... (省略 {{len(data) - 10}} 個鍵)")
                
else:
    # 一般文字檔
    with open('{filename}', 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\\n')
        
        print(f"✅ 文字檔分析")
        print(f"總行數: {{len(lines)}}")
        print(f"總字元數: {{len(content)}}")
        print(f"\\n內容預覽（前 500 字元）:")
        print(content[:500])
        if len(content) > 500:
            print(f"\\n... (剩餘 {{len(content) - 500}} 字元)")
"""
    
    def _generate_statistics_code(self, filename: str) -> str:
        """生成統計分析程式碼"""
        return f"""
import os

file_ext = os.path.splitext('{filename}')[1].lower()

print(f"📈 統計分析: {filename}")
print()

if file_ext == '.csv':
    import csv
    with open('{filename}', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        if not rows:
            print("檔案為空")
        else:
            print(f"✅ CSV 統計資訊")
            print(f"總行數: {{len(rows)}}")
            print(f"欄位數: {{len(rows[0].keys())}}")
            print(f"\\n欄位清單:")
            
            for col in rows[0].keys():
                # 計算非空值數量
                non_empty = sum(1 for row in rows if row.get(col, '').strip())
                print(f"  - {{col}}: {{non_empty}}/{{len(rows)}} 筆有值")
            
elif file_ext == '.json':
    import json
    with open('{filename}', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        print(f"✅ JSON 統計資訊")
        if isinstance(data, list):
            print(f"陣列長度: {{len(data)}}")
            if data and isinstance(data[0], dict):
                print(f"物件欄位: {{', '.join(data[0].keys())}}")
        elif isinstance(data, dict):
            print(f"物件鍵數量: {{len(data.keys())}}")
            print(f"主要鍵值: {{', '.join(list(data.keys())[:5])}}")
else:
    with open('{filename}', 'r', encoding='utf-8') as f:
        content = f.read()
        words = content.split()
        lines = content.split('\\n')
        
        print(f"✅ 文字統計")
        print(f"總字數: {{len(words)}}")
        print(f"總行數: {{len(lines)}}")
        print(f"總字元數: {{len(content)}}")
        print(f"平均每行字數: {{len(words) / len(lines) if lines else 0:.1f}}")
"""
    
    def _extract_result(self, response: Any) -> str:
        """
        從響應中提取結果
        
        Args:
            response: Code Interpreter 響應
        
        Returns:
            結果文字
        """
        result_text = ""
        
        try:
            # 處理 streaming response
            for event in response.get("stream", []):
                if "result" in event:
                    event_result = event["result"]
                    
                    # 處理不同的結果格式
                    if isinstance(event_result, dict):
                        # 提取文字輸出
                        if "output" in event_result:
                            result_text += str(event_result["output"])
                        elif "text" in event_result:
                            result_text += str(event_result["text"])
                        else:
                            result_text += str(event_result)
                    else:
                        result_text += str(event_result)
            
            # 清理結果
            result_text = result_text.strip()
            
            if not result_text:
                result_text = "處理完成，但無輸出內容"
            
            return result_text
            
        except Exception as e:
            logger.error(f"結果提取異常: {str(e)}", exc_info=True)
            return f"結果提取時發生問題: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """
        取得檔案服務狀態
        
        Returns:
            狀態資訊字典
        """
        return {
            "enabled": self.enabled,
            "bucket": self.bucket if self.enabled else None,
            "region": self.region,
            "available": self.is_available()
        }


# 建立全域檔案服務實例
file_service = FileService(settings.AWS_REGION)
