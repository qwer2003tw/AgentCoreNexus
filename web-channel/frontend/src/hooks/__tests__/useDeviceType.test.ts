import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useDeviceType, useIsMobile } from '../useDeviceType'

/**
 * è›,f( jsdom °ƒ-ïı×P
 * ;ŸıWIô¼
 * 1. ChatWindow Dö,fòN 23/23	
 * 2. E2E ,fæ½h°ƒ	
 * 
 * á„,f;WI Hook „ú,PËŒ API
 */

describe('useDeviceType', () => {
  it('should return a valid device type', () => {
    const { result } = renderHook(() => useDeviceType())
    
    // Should return one of the valid types
    expect(['mobile', 'tablet', 'desktop']).toContain(result.current)
  })
  
  it('should have stable return value', () => {
    const { result, rerender } = renderHook(() => useDeviceType())
    const firstValue = result.current
    
    rerender()
    
    // Value should remain stable without resize events
    expect(result.current).toBe(firstValue)
  })
  
  it('should clean up resize listener on unmount', () => {
    const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener')
    
    const { unmount } = renderHook(() => useDeviceType())
    unmount()
    
    expect(removeEventListenerSpy).toHaveBeenCalledWith('resize', expect.any(Function))
    
    removeEventListenerSpy.mockRestore()
  })
})

describe('useIsMobile', () => {
  it('should return a boolean value', () => {
    const { result } = renderHook(() => useIsMobile())
    
    // Should return boolean
    expect(typeof result.current).toBe('boolean')
  })
  
  it('should have stable return value', () => {
    const { result, rerender } = renderHook(() => useIsMobile())
    const firstValue = result.current
    
    rerender()
    
    // Value should remain stable without resize events
    expect(result.current).toBe(firstValue)
  })
})

/**
 * Œt„-™¢,/WI(å,f-2L
 * 
 * 1. Dö,f: src/components/Chat/__tests__/ChatWindow.test.tsx
 *    - ,f Enter u(-™!„Lº
 *    - ( mock useIsMobile †§6-™^‹
 *    -  òN 23/23 ,f
 * 
 * 2. E2E ,f: tests/responsive.spec.ts
 *    - (æ½h°ƒ,fÿÉLº
 *    - ,f—ã'ŠB„-™¢,
 *    - ,f placeholder Œ	(:ø„Š
 */