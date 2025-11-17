"""
Example usage of the IIIF Region Extractor for extracting high-resolution regions from IIIF manifests.

This demonstrates how to extract high-quality image regions from various
types of IIIF manifests commonly found in digital libraries and archives.
"""

import asyncio
from pathlib import Path
from iiif_tile_extractor import IIIFRegionExtractor, extract_iiif_regions

async def basic_example():
    """Basic example: Extract high-resolution regions."""
    print("🔍 Basic Example: Extracting high-resolution regions")
    
    manifest_url = "https://eap.bl.uk/archive-file/EAP532-2-1-1/manifest"
    
    results = await extract_iiif_regions(
        manifest_url=manifest_url,
        target_size=2048,  # Target 2048x2048 regions
        output_dir="./regions_basic/",
        overlap=128,  # 128px overlap between regions
        format="jpg"
    )
    
    print(f"✅ Extracted {results['summary']['total_regions']} regions")
    return results


async def advanced_example():
    """Advanced example with custom settings."""
    print("\n🚀 Advanced Example: Custom headers and settings")
    
    # Custom headers for authentication or identification
    headers = {
        "User-Agent": "Research Project - IIIF Region Analysis v1.0",
        "Accept": "image/jpeg,image/png,*/*"
    }
    
    extractor = IIIFRegionExtractor(headers=headers)
    manifest_url = "https://eap.bl.uk/archive-file/EAP532-2-1-1/manifest"
    
    results = await extractor.extract_iiif_regions(
        manifest_url=manifest_url,
        target_size=4096,  # Very large regions for maximum detail
        output_dir="./regions_advanced/",
        overlap=256,  # Large overlap for seamless stitching
        format="png",  # Lossless format
        quality="color",
        max_concurrent=2  # Conservative for large files
    )
    
    print(f"✅ Extracted {results['summary']['total_regions']} high-quality regions")
    return results


async def batch_processing():
    """Process multiple manifests in batch."""
    print("\n📋 Batch Processing: Multiple manifests")
    
    manifests = [
        "https://eap.bl.uk/archive-file/EAP532-2-1-1/manifest",
        "https://eap.bl.uk/archive-file/EAP699-23-1/manifest",
        "https://eap.bl.uk/archive-file/EAP1251-1-22-2-2/manifest"
    ]
    
    extractor = IIIFRegionExtractor()
    
    for i, manifest_url in enumerate(manifests, 1):
        try:
            print(f"\n  Processing manifest {i}/{len(manifests)}...")
            
            results = await extractor.extract_iiif_regions(
                manifest_url=manifest_url,
                target_size=1536,
                output_dir=f"./batch_regions/item_{i:02d}/",
                overlap=96,
                format="jpg",
                max_concurrent=4
            )
            
            print(f"  ✅ Item {i}: {results['summary']['total_regions']} regions")
            
        except Exception as e:
            print(f"  ❌ Error with item {i}: {e}")


async def size_optimization_example():
    """Demonstrate different target sizes for various use cases."""
    print("\n📏 Size Optimization: Different target sizes")
    
    manifest_url = "https://eap.bl.uk/archive-file/EAP532-2-1-1/manifest"
    
    size_configs = [
        {"size": 1024, "use_case": "OCR processing", "overlap": 64},
        {"size": 2048, "use_case": "General analysis", "overlap": 128},
        {"size": 4096, "use_case": "High-detail work", "overlap": 256}
    ]
    
    extractor = IIIFRegionExtractor()
    
    for config in size_configs:
        try:
            print(f"\n  Testing {config['size']}px regions for {config['use_case']}...")
            
            results = await extractor.extract_iiif_regions(
                manifest_url=manifest_url,
                target_size=config["size"],
                output_dir=f"./size_test/{config['size']}px/",
                overlap=config["overlap"],
                format="jpg",
                max_concurrent=3
            )
            
            total_regions = results['summary']['total_regions']
            processing_time = results['summary']['processing_time']
            
            print(f"  ✅ {total_regions} regions in {processing_time:.1f}s")
            
        except Exception as e:
            print(f"  ❌ Error with {config['size']}px: {e}")


async def main():
    """Run all examples."""
    print("🎯 IIIF Region Extractor Examples")
    print("=" * 50)
    
    # Create output directories
    Path("regions_basic").mkdir(exist_ok=True)
    Path("regions_advanced").mkdir(exist_ok=True)
    Path("batch_regions").mkdir(exist_ok=True)
    Path("size_test").mkdir(exist_ok=True)
    
    try:
        # Run examples
        await basic_example()
        await advanced_example()
        await batch_processing()
        await size_optimization_example()
        
        print("\n" + "=" * 50)
        print("🎉 All examples completed successfully!")
        print("\nOutput directories:")
        print("  - regions_basic/     - Basic high-res regions")
        print("  - regions_advanced/  - PNG regions with custom settings")
        print("  - batch_regions/     - Batch processed manifests")
        print("  - size_test/         - Different region sizes")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())