"""
Test script for Qwen VL bounding box extraction.
Run this to test if Qwen VL can locate text in resume PDFs.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.qwen_vl import test_extract_bbox

def main():
    # Test with a sample resume
    pdf_path = r"c:\Users\nnurs\Desktop\NeuralHire\site\mysite\media\resumes\Повар.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        pdf_path = input("Enter path to test resume PDF: ").strip()
    
    # Test keywords
    test_keywords = [
        "Москва",
        "повар",
        "кухня",
    ]
    
    print("\n" + "="*60)
    print("TESTING QWEN VL BOUNDING BOX EXTRACTION")
    print("="*60)
    
    for keyword in test_keywords:
        print(f"\nTesting keyword: '{keyword}'")
        result = test_extract_bbox(pdf_path, keyword)
        
        if result:
            print(f"✓ SUCCESS for '{keyword}':")
            print(f"  Page: {result['page']}")
            print(f"  BBox: {result['bbox']}")
            print(f"  Text: {result.get('text', 'N/A')}")
        else:
            print(f"✗ FAILED for '{keyword}': Not found")
        
        print("-" * 60)
    
    print("\nTest complete!")

if __name__ == "__main__":
    main()
