# IIIF Manifest Tile Extraction Requirements

## Overview
Create a function that processes IIIF manifests to extract high-resolution image regions directly from IIIF endpoints. Instead of downloading low-resolution full images, use IIIF's region parameters to fetch larger, more readable tiles at maximum available resolution for improved analysis and processing.

## Core Requirements

### 1. IIIF Manifest Processing
- **Read IIIF Manifest**: Parse JSON manifest from URL or local file
- **Extract Image Information**: Get all images from canvases in sequences
- **Handle IIIF Versions**: Support IIIF API versions 2.x and 3.x
- **Service Discovery**: Find IIIF Image API service endpoints
- **Error Handling**: Graceful handling of malformed or incomplete manifests

### 2. Maximum Resolution Discovery
- **Service Info Parsing**: Fetch `info.json` to get maximum available dimensions
- **Size Limits**: Determine server's `maxWidth`, `maxHeight`, and `maxArea` constraints
- **Scale Factors**: Identify available scale factors and size options
- **Format Support**: Check supported output formats and quality levels
- **Tile Size Limits**: Respect server's maximum tile dimensions

### 3. High-Resolution Region Calculation
- **Target Resolution**: Calculate optimal tile size for maximum quality without exceeding limits
- **Grid Planning**: Determine how many tiles needed to cover full image at high resolution
- **Region Boundaries**: Calculate precise `x,y,w,h` coordinates for each region
- **Size Optimization**: Request largest possible size for each region within server limits
- **Overlap Handling**: Optional overlap between adjacent tiles for seamless processing

### 4. IIIF Region Requests
- **Direct Region Fetching**: Use IIIF `/region/size/` syntax to get high-res tiles
- **Maximum Size Requests**: Request largest available size for each region
- **Quality Selection**: Choose best available quality (usually 'default' or 'color')
- **Format Optimization**: Select most appropriate format (jpg for photos, png for line art)
- **Server Compliance**: Respect server's advertised capabilities and limits

### 5. Smart Tiling Strategy
- **Adaptive Sizing**: Adjust tile dimensions based on server capabilities
- **Edge Region Handling**: Handle partial regions at image boundaries intelligently  
- **Memory Efficiency**: Download regions without storing full image in memory
- **Progressive Coverage**: Cover image systematically from top-left to bottom-right
- **Metadata Tracking**: Record actual dimensions and coordinates of each fetched region

## Technical Specifications

### Function Signature
```python
def extract_iiif_regions(
    manifest_url: str,
    output_dir: str,
    target_size: int = 2048,
    overlap: int = 0,
    format: str = "jpg",
    quality: str = "default", 
    max_concurrent: int = 10,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
```

### Input Parameters
- `manifest_url`: URL or local path to IIIF manifest
- `output_dir`: Directory to save extracted high-resolution regions
- `target_size`: Target pixel size for regions (will be adjusted based on server limits)
- `overlap`: Pixel overlap between adjacent regions (for seamless processing)
- `format`: Image format for regions (jpg, png, webp, tif)
- `quality`: IIIF quality parameter (default, color, gray, bitonal)
- `max_concurrent`: Maximum concurrent downloads
- `headers`: Optional HTTP headers (e.g., User-Agent)

### Return Value
```python
{
    "manifest_info": {
        "title": str,
        "total_images": int,
        "iiif_version": str
    },
    "extraction_results": [
        {
            "image_id": str,
            "canvas_label": str,
            "original_dimensions": {"width": int, "height": int},
            "zoom_level": int,
            "scale_factor": float,
            "tile_dimensions": {"width": int, "height": int},
            "tiles_extracted": int,
            "grid_size": {"columns": int, "rows": int},
            "output_directory": str,
            "success": bool,
            "errors": List[str]
        }
    ],
    "summary": {
        "total_tiles": int,
        "successful_downloads": int,
        "failed_downloads": int,
        "total_time": float
    }
}
```

## Detailed Requirements

### 1. Manifest Parsing
- Parse `sequences[0].canvases` to get all image canvases
- Extract `images[0].resource` or `body` (IIIF v3) for image information
- Handle both `@id` (v2) and `id` (v3) properties
- Support `service` property for IIIF Image API endpoints
- Validate required properties exist

### 2. Image Service Detection
- Identify IIIF Image API service URLs
- Parse `info.json` endpoints for complete image information
- Handle different service URL patterns:
  - `{scheme}://{server}{/prefix}/{identifier}`
  - Direct image URLs with IIIF parameters
- Support authentication if required

### 3. High-Resolution Strategy
```
Goal: Extract regions at maximum available resolution
Strategy: Use largest possible region size within server limits
Approach: Request regions directly via IIIF, not zoom levels
Quality: Prioritize resolution over coverage completeness
```

### 4. IIIF Region URL Generation  
Follow IIIF Image API URL pattern for maximum resolution:
```
{scheme}://{server}{/prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
```

Where:
- `region`: `x,y,w,h` pixel coordinates at full resolution
- `size`: `max` or specific `w,h` constrained by server limits  
- `rotation`: Usually `0`
- `quality`: `default` (highest available) or `color`
- `format`: `jpg` (universal) or `png` (lossless)

### 5. Error Handling
- **Network Errors**: Retry failed requests with exponential backoff
- **HTTP Errors**: Handle 404, 403, 500 status codes appropriately  
- **Invalid Tiles**: Skip tiles that exceed image boundaries
- **Service Unavailable**: Graceful degradation when IIIF service is down
- **Manifest Errors**: Clear error messages for invalid manifests

### 6. Performance Requirements
- **Concurrent Downloads**: Configurable parallel tile downloads
- **Progress Tracking**: Rich progress bars for long operations  
- **Memory Efficiency**: Stream downloads without loading all tiles in memory
- **Resumable**: Skip existing tiles to allow resuming interrupted downloads
- **Rate Limiting**: Respect server capabilities and avoid overwhelming endpoints

### 7. Output Organization
```
output_dir/
├── manifest_info.json
├── image_001/
│   ├── tile_metadata.json
│   ├── zoom_2/
│   │   ├── tile_0_0.jpg
│   │   ├── tile_0_1.jpg
│   │   └── tile_1_0.jpg
│   └── zoom_3/
│       └── ...
└── image_002/
    └── ...
```

### 8. Metadata Files
- **manifest_info.json**: Complete manifest metadata
- **tile_metadata.json**: Per-image tile organization info
- **Tile naming**: `tile_{column}_{row}.{format}`
- **Coordinate tracking**: Preserve original IIIF coordinates

## Dependencies
- `requests` or `httpx`: HTTP client for manifest and tile downloads
- `rich`: Progress bars and console output
- `pathlib`: File path handling
- `asyncio`/`aiohttp`: Async downloads for performance
- `PIL/Pillow`: Optional image validation and processing
- `json`: JSON manifest parsing

## Testing Requirements
- Unit tests for manifest parsing with various IIIF versions
- Integration tests with real IIIF endpoints
- Error handling tests for malformed data
- Performance tests with large manifests
- Validation of tile coordinate calculations
- Cross-platform compatibility testing

## Usage Examples

### Basic Usage
```python
# Extract high-resolution regions from IIIF manifest
results = extract_iiif_regions(
    manifest_url="https://example.org/manifest.json",
    output_dir="./high_res_regions/",
    target_size=2048  # Request ~2K regions for maximum quality
)
```

### Advanced Usage
```python
# Custom settings for overlapping regions
results = extract_iiif_regions(
    manifest_url="https://library.example.org/manifest.json", 
    output_dir="./overlapping_regions/",
    target_size=4096,  # Try for 4K regions if server supports
    overlap=256,       # 256px overlap for seamless stitching
    format="png",      # Lossless format
    quality="color",
    max_concurrent=3,  # Conservative to avoid overwhelming server
    headers={"User-Agent": "Research Project v1.0"}
)
```

### Maximum Resolution Extraction
```python
# Extract at absolute maximum available resolution
results = extract_iiif_regions(
    manifest_url="https://collections.example.edu/manifest.json",
    output_dir="./max_resolution/",
    target_size=8192,  # Request very large regions
    overlap=512,       # Large overlap for ML training
    format="tiff",     # Maximum quality format
    quality="default", # Best available quality
    max_concurrent=1   # Single threaded for stability
)
```

## Future Enhancements
- Support for IIIF Collections (multiple manifests)
- Tile merging for creating larger composite images
- Integration with machine learning preprocessing pipelines
- Support for IIIF Authentication API
- Caching layer for frequently accessed tiles
- Tile format conversion and optimization
