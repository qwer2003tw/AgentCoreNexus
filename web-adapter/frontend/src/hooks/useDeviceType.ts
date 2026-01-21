import { useState, useEffect } from 'react'

export type DeviceType = 'mobile' | 'tablet' | 'desktop'

/**
 * 檢測設備類型的 Hook
 * 結合屏幕寬度、觸控能力和 User Agent 進行綜合判斷
 * 
 * @returns DeviceType - 'mobile' | 'tablet' | 'desktop'
 */
export function useDeviceType(): DeviceType {
  const [deviceType, setDeviceType] = useState<DeviceType>('desktop')
  
  useEffect(() => {
    let timeoutId: NodeJS.Timeout | null = null
    
    const checkDeviceType = () => {
      // 使用 debounce 避免頻繁計算
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      
      timeoutId = setTimeout(() => {
        // 檢查 1: Touch capability
        const hasTouchScreen = (
          'ontouchstart' in window || 
          navigator.maxTouchPoints > 0
        )
        
        // 檢查 2: Screen width
        const width = window.innerWidth
        
        // 檢查 3: User Agent (備用方案)
        const userAgent = navigator.userAgent.toLowerCase()
        const isMobileUA = /mobile|android|iphone|ipod|blackberry|iemobile|opera mini/i.test(userAgent)
        const isTabletUA = /tablet|ipad|playbook|silk/i.test(userAgent)
        
        // 綜合判斷
        let newDeviceType: DeviceType
        
        if (width < 768) {
          // 小於 768px = 手機
          newDeviceType = 'mobile'
        } else if (width < 1024) {
          // 768-1024px = 平板（默認視為移動設備）
          // 即使沒有觸控也視為平板（避免測試環境問題）
          newDeviceType = 'tablet'
        } else if (hasTouchScreen && isMobileUA) {
          // 有觸控 + 手機 UA = 手機
          newDeviceType = 'mobile'
        } else {
          // 其他 = 桌面
          newDeviceType = 'desktop'
        }
        
        setDeviceType(newDeviceType)
      }, 150) // debounce 150ms
    }
    
    // 初始檢測
    checkDeviceType()
    
    // 監聽窗口大小變化（處理旋轉、窗口調整）
    window.addEventListener('resize', checkDeviceType)
    
    // 清理
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      window.removeEventListener('resize', checkDeviceType)
    }
  }, [])
  
  return deviceType
}

/**
 * 便利函數：檢測是否為移動設備（包含手機和平板）
 * 
 * @returns boolean - true 表示移動設備（手機或平板）
 */
export function useIsMobile(): boolean {
  const deviceType = useDeviceType()
  return deviceType === 'mobile' || deviceType === 'tablet'
}