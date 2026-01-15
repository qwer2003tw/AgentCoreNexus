import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import AttachmentItem from '../AttachmentItem'

// Mock api module
vi.mock('@/services/api', () => ({
  api: {
    getAttachmentDownloadUrl: vi.fn().mockResolvedValue({
      download_url: 'https://example.com/download'
    })
  }
}))

describe('AttachmentItem', () => {
  it('should handle missing content_type gracefully', () => {
    const attachment = {
      id: '1',
      name: 'test.txt',
      size: 1024,
      content_type: undefined as any,  // Test undefined case
      key: 'test/key.txt'
    }
    
    // Should not crash
    expect(() => {
      render(<AttachmentItem attachment={attachment} />)
    }).not.toThrow()
    
    // Should display file name
    expect(screen.getByText('test.txt')).toBeInTheDocument()
    
    // Should display file size
    expect(screen.getByText('1.0 KB')).toBeInTheDocument()
  })
  
  it('should correctly identify images when content_type is present', () => {
    const attachment = {
      id: '2',
      name: 'photo.jpg',
      size: 2048,
      content_type: 'image/jpeg',
      key: 'test/photo.jpg'
    }
    
    render(<AttachmentItem attachment={attachment} />)
    
    expect(screen.getByText('photo.jpg')).toBeInTheDocument()
    expect(screen.getByText('2.0 KB')).toBeInTheDocument()
  })
  
  it('should treat files with undefined content_type as non-images', () => {
    const attachment = {
      id: '3',
      name: 'document.pdf',
      size: 4096,
      content_type: undefined as any,
      key: 'test/doc.pdf'
    }
    
    const { container } = render(<AttachmentItem attachment={attachment} />)
    
    // Should render without errors
    expect(screen.getByText('document.pdf')).toBeInTheDocument()
    
    // Should not show image-specific preview button
    const previewButtons = container.querySelectorAll('button')
    // Should only have download button (not preview)
    expect(previewButtons).toHaveLength(1)
  })
  
  it('should handle empty string content_type', () => {
    const attachment = {
      id: '4',
      name: 'file.dat',
      size: 512,
      content_type: '',
      key: 'test/file.dat'
    }
    
    expect(() => {
      render(<AttachmentItem attachment={attachment} />)
    }).not.toThrow()
    
    expect(screen.getByText('file.dat')).toBeInTheDocument()
  })
})