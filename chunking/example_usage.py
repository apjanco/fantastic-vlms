"""
Example usage of the IIIF Tile Extractor

This script demonstrates how to use the IIIF tile extraction functionality
with various configurations and use cases.
"""

import asyncio
from iiif_tile_extractor import extract_iiif_tiles, IIIFTileExtractor


async def basic_example():
    """Basic example: Extract tiles at zoom level 3 (1:8 scale)."""
    print("🔍 Basic Example: Extracting tiles at zoom level 3")
    
    manifest_url = "https://eap.bl.uk/archive-file/EAP1477-1-1-1/manifest"
    
    results = await extract_iiif_tiles(
        manifest_url=manifest_url,
        zoom_level=3,
        output_dir="./tiles_basic/",
        tile_size=256,
        format="jpg"
    )
    
    print(f"✅ Extracted {results['summary']['total_tiles']} tiles")
    return results


async def advanced_example():
    """Advanced example with custom settings."""
    print("\n🚀 Advanced Example: Custom headers and settings")
    
    # Custom headers for authentication or identification
    headers = {
        "User-Agent": "Research Project - IIIF Tile Analysis v1.0",
        "Accept": "image/jpeg,image/png,*/*"
    }
    
    manifest_url = "https://eap.bl.uk/archive-file/EAP1477-1-1-1/manifest"
    
    results = await extract_iiif_tiles(
        manifest_url=manifest_url,
        zoom_level=2,  # Higher resolution (1:4 scale)
        output_dir="./tiles_advanced/",
        tile_size=1024,  # Larger tiles
        format="png",
        quality="color",
        max_concurrent=3,  # Conservative concurrent downloads
        headers=headers
    )
    
    return results


async def class_based_example():
    """Example using the class directly for more control."""
    print("\n⚙️  Class-based Example: Direct class usage")
    
    # Create extractor instance
    extractor = IIIFTileExtractor(headers={
        "User-Agent": "Custom IIIF Client v1.0"
    })
    
    manifest_url = "https://eap.bl.uk/archive-file/EAP1477-1-1-1/manifest"
    
    results = await extractor.extract_iiif_tiles(
        manifest_url=manifest_url,
        zoom_level=4,  # Lower resolution for quick testing
        output_dir="./tiles_class/",
        tile_size=512,
        format="jpg",
        quality="default",
        max_concurrent=8
    )
    
    # Access detailed results
    for img_result in results['extraction_results']:
        print(f"  📷 {img_result['canvas_label']}: "
              f"{img_result['tiles_extracted']} tiles, "
              f"Grid: {img_result['grid_size']['columns']}x{img_result['grid_size']['rows']}")
    
    return results


async def multiple_zoom_levels():
    """Extract tiles at multiple zoom levels for the same manifest."""
    print("\n📚 Multi-zoom Example: Multiple zoom levels")
    
    manifest_url = "https://eap.bl.uk/archive-file/EAP1477-1-1-1/manifest"
    zoom_levels = [2, 3, 4]  # Different resolutions
    
    all_results = []
    
    for zoom in zoom_levels:
        print(f"\n  🔍 Processing zoom level {zoom}")
        
        results = await extract_iiif_tiles(
            manifest_url=manifest_url,
            zoom_level=zoom,
            output_dir=f"./tiles_multi_zoom/zoom_{zoom}/",
            tile_size=512,
            format="jpg",
            max_concurrent=5
        )
        
        all_results.append({
            'zoom_level': zoom,
            'results': results
        })
        
        print(f"    ✅ Zoom {zoom}: {results['summary']['total_tiles']} tiles")
    
    return all_results


async def local_manifest_example():
    """Example using a local manifest file."""
    print("\n📁 Local Manifest Example")
    
    # First, let's download a manifest to use locally
    manifest_url = "https://eap.bl.uk/archive-file/EAP1477-1-1-1/manifest"
    
    import aiohttp
    import json
    
    # Download manifest
    async with aiohttp.ClientSession() as session:
        async with session.get(manifest_url) as response:
            manifest_data = await response.json()
    
    # Save locally
    local_manifest_path = "./local_manifest.json"
    with open(local_manifest_path, 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    print(f"  📥 Downloaded manifest to: {local_manifest_path}")
    
    # Now use the local manifest
    results = await extract_iiif_tiles(
        manifest_url=local_manifest_path,  # Local file path
        zoom_level=3,
        output_dir="./tiles_local/",
        tile_size=256
    )
    
    return results


async def error_handling_example():
    """Demonstrate error handling with invalid URLs."""
    print("\n⚠️  Error Handling Example")
    
    try:
        # This should fail gracefully
        results = await extract_iiif_tiles(
            manifest_url="https://invalid-url-that-does-not-exist.com/manifest.json",
            zoom_level=2,
            output_dir="./tiles_error_test/",
            tile_size=512
        )
    except Exception as e:
        print(f"  ❌ Expected error caught: {type(e).__name__}: {e}")
    
    # Test with invalid local file
    try:
        results = await extract_iiif_tiles(
            manifest_url="./nonexistent_manifest.json",
            zoom_level=2,
            output_dir="./tiles_error_test2/",
            tile_size=512
        )
    except Exception as e:
        print(f"  ❌ Expected error caught: {type(e).__name__}: {e}")


async def main():
    """Run all examples."""
    print("🎯 IIIF Tile Extractor Examples")
    print("=" * 50)
    
    try:
        # Run basic example
        await basic_example()
        
        # Run advanced example  
        await advanced_example()
        
        # Run class-based example
        await class_based_example()
        
        # Run multiple zoom levels
        await multiple_zoom_levels()
        
        # Run local manifest example
        await local_manifest_example()
        
        # Run error handling example
        await error_handling_example()
        
        print("\n🎉 All examples completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")


if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        import aiohttp
        import aiofiles
        from rich.progress import Progress
        from rich.console import Console
    except ImportError as e:
        print("❌ Missing required packages. Please install:")
        print("   pip install aiohttp aiofiles rich")
        exit(1)
    
    # Run examples
    asyncio.run(main())