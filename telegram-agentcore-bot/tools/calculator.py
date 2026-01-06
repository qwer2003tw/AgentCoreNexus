"""
數學計算工具
提供安全的數學表達式計算
"""
from strands import tool
from utils.logger import get_logger
from config.prompts import get_error_message

logger = get_logger(__name__)

@tool
def calculate(expression: str) -> str:
    """
    執行簡單數學計算（安全版本）
    
    Args:
        expression: 數學表達式
    
    Returns:
        計算結果或錯誤訊息
    """
    logger.info(f"計算表達式: {expression}")
    
    try:
        # 定義允許的字元集合（只允許基本數學運算）
        allowed_chars = set("0123456789+-*/.(). ")
        
        # 檢查表達式是否只包含允許的字元
        if not all(c in allowed_chars for c in expression):
            error_msg = "只允許基本數學運算 (+, -, *, /, 括號)"
            logger.warning(f"計算失敗: {error_msg}")
            return f"❌ {error_msg}"
        
        # 安全地執行計算（限制 builtins）
        result = eval(expression, {"__builtins__": {}}, {})
        
        # 格式化結果
        if isinstance(result, float):
            # 如果是整數值，顯示為整數
            if result.is_integer():
                result = int(result)
            else:
                # 限制小數位數
                result = round(result, 6)
        
        logger.info(f"計算成功: {result}")
        return f"計算結果: {result}"
        
    except ZeroDivisionError:
        error_msg = "除數不能為零"
        logger.warning(f"計算錯誤: {error_msg}")
        return get_error_message("calculation_error", error=error_msg)
        
    except SyntaxError:
        error_msg = "表達式語法錯誤"
        logger.warning(f"計算錯誤: {error_msg}")
        return get_error_message("calculation_error", error=error_msg)
        
    except Exception as e:
        logger.error(f"計算異常: {str(e)}", exc_info=True)
        return get_error_message("calculation_error", error=str(e))
