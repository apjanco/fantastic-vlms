"""
IIIF High-Resolution Region Extractor

A comprehensive function for extracting high-resolution regions directly from IIIF manifests.
Instead of downloading low-resolution full images, uses IIIF region parameters to fetch 
maximum quality regions for improved analysis and processing.
Supports IIIF Image API v2.x and v3.x with concurrent downloads and progress tracking.
"""

import asyncio
import aiohttp
import aiofiles
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
import time
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.console import Console
import re


class IIIFRegionExtractor:
    """Extract high-resolution regions directly from IIIF manifests."""
    
    def __init__(self, headers: Optional[Dict[str, str]] = None):
        self.headers = headers or {
            "User-Agent": "IIIF-Tile-Extractor/1.0 (Research Tool)"
        }
        self.console = Console()
    
    async def extract_iiif_regions(
        self,
        manifest_url: str,
        output_dir: str,
        target_size: int = 2048,
        overlap: int = 0,
        format: str = "jpg",
        quality: str = "default",
        max_concurrent: int = 10,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Extract high-resolution regions from IIIF manifest.
        
        Args:
            manifest_url: URL or local path to IIIF manifest
            output_dir: Directory to save extracted high-resolution regions
            target_size: Target pixel size for regions (adjusted based on server limits)
            overlap: Pixel overlap between adjacent regions (for seamless processing)
            format: Image format for regions (jpg, png, webp, tif)
            quality: IIIF quality parameter (default, color, gray, bitonal)
            max_concurrent: Maximum concurrent downloads
            headers: Optional HTTP headers
            
        Returns:
            Dictionary with extraction results and metadata
        """
        if headers:
            self.headers.update(headers)
        
        start_time = time.time()
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Load and parse manifest
            self.console.print("📋 Loading IIIF manifest...", style="blue")
            manifest = await self._load_manifest(manifest_url)
            manifest_info = self._parse_manifest_info(manifest)
            
            # Save manifest info
            manifest_info_path = output_path / "manifest_info.json"
            with open(manifest_info_path, 'w') as f:
                json.dump(manifest_info, f, indent=2)
            
            # Extract images from manifest
            images = self._extract_images_from_manifest(manifest)
            
            if not images:
                raise ValueError("No images found in manifest")
            
            self.console.print(f"🖼️  Found {len(images)} images in manifest", style="green")
            
            # Process each image
            extraction_results = []
            total_tiles = 0
            successful_downloads = 0
            failed_downloads = 0
            
            for idx, image_info in enumerate(images):
                self.console.print(f"\n🔍 Processing image {idx + 1}/{len(images)}: {image_info['canvas_label']}")
                
                result = await self._process_image(
                    image_info, 
                    output_path, 
                    target_size,
                    overlap,
                    format, 
                    quality, 
                    max_concurrent
                )
                
                extraction_results.append(result)
                total_tiles += result['regions_extracted']
                successful_downloads += result.get('successful_regions', 0)
                failed_downloads += len(result.get('errors', []))
            
            total_time = time.time() - start_time
            
            # Compile final results
            results = {
                "manifest_info": manifest_info,
                "extraction_results": extraction_results,
                "summary": {
                    "total_regions": total_tiles,
                    "successful_downloads": successful_downloads,
                    "failed_downloads": failed_downloads,
                    "total_time": total_time
                }
            }
            
            # Save complete results
            results_path = output_path / "extraction_results.json"
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.console.print(f"\n✅ Extraction complete!", style="bold green")
            self.console.print(f"📊 Total regions: {total_tiles}")
            self.console.print(f"✅ Successful: {successful_downloads}")
            self.console.print(f"❌ Failed: {failed_downloads}")
            self.console.print(f"⏱️  Total time: {total_time:.2f} seconds")
            
            return results
            
        except Exception as e:
            self.console.print(f"❌ Error during extraction: {str(e)}", style="red")
            raise
    
    async def _load_manifest(self, manifest_url: str) -> Dict[str, Any]:
        """Load manifest from URL or local file."""
        if manifest_url.startswith(('http://', 'https://')):
            # Enhanced headers to avoid being blocked
            manifest_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, application/ld+json, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Update with any custom headers
            if self.headers:
                manifest_headers.update(self.headers)
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(headers=manifest_headers, timeout=timeout) as session:
                try:
                    async with session.get(manifest_url) as response:
                        #response.raise_for_status()
                        
                        # Check content type
                        content_type = response.headers.get('content-type', '').lower()
                        
                        if 'application/json' in content_type or 'application/ld+json' in content_type:
                            return await response.json()
                        else:
                            # Try to parse as JSON even if content-type is wrong
                            text_content = await response.text()
                            try:
                                return json.loads(text_content)
                            except json.JSONDecodeError:
                                # If that fails, check if it's HTML (blocked request)
                                if '<html' in text_content.lower():
                                    raise ValueError(f"Server returned HTML instead of JSON. This may indicate the request was blocked or redirected. Content-Type: {content_type}")
                                else:
                                    raise ValueError(f"Invalid JSON content received. Content-Type: {content_type}")
                
                except aiohttp.ClientResponseError as e:
                    if e.status == 403:
                        raise ValueError(f"Access forbidden (403). The server may be blocking requests. Try different headers or check if authentication is required.")
                    elif e.status == 404:
                        raise ValueError(f"Manifest not found (404). Check if the URL is correct: {manifest_url}")
                    else:
                        raise ValueError(f"HTTP error {e.status}: {e.message}")
                
                except asyncio.TimeoutError:
                    raise ValueError(f"Request timeout. The server may be slow or unreachable: {manifest_url}")
        else:
            # Local file
            with open(manifest_url, 'r') as f:
                return json.load(f)
    
    def _parse_manifest_info(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic information from manifest."""
        # Determine IIIF version
        context = manifest.get('@context', manifest.get('context', ''))
        if '3' in str(context):
            iiif_version = '3.x'
        elif '2' in str(context):
            iiif_version = '2.x'
        else:
            iiif_version = 'unknown'
        
        # Extract title (handle both v2 and v3)
        title = None
        if 'label' in manifest:
            label = manifest['label']
            if isinstance(label, dict):
                # IIIF v3 format
                title = next(iter(label.values()))[0] if label else "Untitled"
            elif isinstance(label, list):
                title = label[0] if label else "Untitled"
            else:
                title = str(label)
        else:
            title = "Untitled"
        
        # Count images
        total_images = 0
        sequences = manifest.get('sequences', manifest.get('items', []))
        for sequence in sequences:
            canvases = sequence.get('canvases', sequence.get('items', []))
            total_images += len(canvases)
        
        return {
            "title": title,
            "total_images": total_images,
            "iiif_version": iiif_version,
            "manifest_id": manifest.get('@id', manifest.get('id', '')),
            "context": context
        }
    
    def _extract_images_from_manifest(self, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract image information from manifest."""
        images = []
        
        sequences = manifest.get('sequences', manifest.get('items', []))
        for sequence in sequences:
            canvases = sequence.get('canvases', sequence.get('items', []))
            
            for canvas in canvases:
                # Get canvas label
                canvas_label = self._extract_label(canvas)
                
                # Extract images from canvas
                canvas_images = canvas.get('images', canvas.get('items', []))
                
                for img in canvas_images:
                    # Handle IIIF v2 vs v3 structure
                    if 'resource' in img:
                        # IIIF v2
                        resource = img['resource']
                        image_id = resource.get('@id', '')
                        service = resource.get('service', {})
                    else:
                        # IIIF v3
                        body = img.get('body', {})
                        image_id = body.get('id', '')
                        service = body.get('service', [])
                        if isinstance(service, list) and service:
                            service = service[0]
                    
                    if image_id:
                        images.append({
                            'image_id': image_id,
                            'canvas_label': canvas_label,
                            'service': service,
                            'canvas': canvas
                        })
        
        return images
    
    def _extract_label(self, item: Dict[str, Any]) -> str:
        """Extract label from IIIF item (works with v2 and v3)."""
        label = item.get('label', 'Untitled')
        
        if isinstance(label, dict):
            # IIIF v3 format
            return next(iter(label.values()))[0] if label else "Untitled"
        elif isinstance(label, list):
            return label[0] if label else "Untitled"
        else:
            return str(label)
    
    async def _process_image(
        self,
        image_info: Dict[str, Any],
        output_path: Path,
        target_size: int,
        overlap: int,
        format: str,
        quality: str,
        max_concurrent: int
    ) -> Dict[str, Any]:
        """Process a single image to extract high-resolution regions."""
        
        try:
            # Get image service info including server limits
            service_info = await self._get_image_service_info(image_info)
            
            # Get original dimensions
            original_width = service_info['width']
            original_height = service_info['height']
            
            # Determine optimal region size based on server constraints
            optimal_size = self._calculate_optimal_region_size(service_info, target_size)
            
            self.console.print(f"  📐 Image: {original_width}x{original_height}, Target: {target_size}px, Optimal: {optimal_size}px")
            
            # Create output directory for this image
            image_dir = output_path / f"image_{self._sanitize_filename(image_info['canvas_label'])}"
            regions_dir = image_dir / "regions"
            regions_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate high-resolution region coordinates
            regions = self._generate_high_res_regions(
                service_info['base_url'],
                original_width,
                original_height,
                optimal_size,
                overlap,
                format,
                quality
            )
            
            # Save region metadata
            region_metadata = {
                "image_id": image_info['image_id'],
                "canvas_label": image_info['canvas_label'],
                "original_dimensions": {"width": original_width, "height": original_height},
                "target_size": target_size,
                "optimal_size": optimal_size,
                "overlap": overlap,
                "grid_size": {"columns": len(set(r['column'] for r in regions)), 
                             "rows": len(set(r['row'] for r in regions))},
                "total_regions": len(regions),
                "server_limits": {
                    "max_width": service_info.get('max_width'),
                    "max_height": service_info.get('max_height'),
                    "max_area": service_info.get('max_area')
                },
                "format": format,
                "quality": quality
            }
            
            metadata_path = image_dir / "region_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(region_metadata, f, indent=2)
            
            # Download regions
            successful_regions, errors = await self._download_regions(
                regions, regions_dir, max_concurrent
            )
            
            return {
                "image_id": image_info['image_id'],
                "canvas_label": image_info['canvas_label'],
                "original_dimensions": {"width": original_width, "height": original_height},
                "target_size": target_size,
                "optimal_size": optimal_size,
                "overlap": overlap,
                "regions_extracted": len(regions),
                "successful_regions": successful_regions,
                "grid_size": {"columns": len(set(r['column'] for r in regions)), 
                             "rows": len(set(r['row'] for r in regions))},
                "output_directory": str(regions_dir),
                "success": len(errors) == 0,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "image_id": image_info.get('image_id', 'unknown'),
                "canvas_label": image_info.get('canvas_label', 'unknown'),
                "success": False,
                "errors": [str(e)]
            }
    
    async def _get_image_service_info(self, image_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get image service information including dimensions."""
        service = image_info.get('service', {})
        
        if isinstance(service, list):
            service = service[0] if service else {}
        
        # Try to get service URL
        service_url = service.get('@id', service.get('id', ''))
        
        if service_url:
            # Fetch info.json
            info_url = service_url.rstrip('/') + '/info.json'
            
            try:
                # Use same enhanced headers as manifest loading
                info_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json, application/ld+json, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                if self.headers:
                    info_headers.update(self.headers)
                
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(headers=info_headers, timeout=timeout) as session:
                    async with session.get(info_url) as response:
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '').lower()
                            
                            if 'application/json' in content_type or 'application/ld+json' in content_type:
                                info = await response.json()
                            else:
                                # Try to parse as JSON anyway
                                text_content = await response.text()
                                info = json.loads(text_content)
                            
                            return {
                                'base_url': service_url,
                                'width': info['width'],
                                'height': info['height'],
                                'max_width': info.get('maxWidth', info['width']),
                                'max_height': info.get('maxHeight', info['height']),
                                'max_area': info.get('maxArea', info['width'] * info['height']),
                                'sizes': info.get('sizes', []),
                                'formats': info.get('formats', ['jpg']),
                                'qualities': info.get('qualities', ['default'])
                            }
            except Exception as e:
                self.console.print(f"⚠️  Could not fetch info.json from {info_url}: {e}", style="yellow")
        
        # Fallback: try to extract from canvas or image
        canvas = image_info.get('canvas', {})
        canvas_width = canvas.get('width', 0)
        canvas_height = canvas.get('height', 0)
        
        if canvas_width and canvas_height:
            # Use image ID as base URL if no service
            image_id = image_info['image_id']
            base_url = image_id.rsplit('/', 1)[0] if '/' in image_id else image_id
            
            return {
                'base_url': base_url,
                'width': canvas_width,
                'height': canvas_height,
                'max_width': canvas_width,
                'max_height': canvas_height,
                'max_area': canvas_width * canvas_height,
                'sizes': [],
                'formats': ['jpg'],
                'qualities': ['default']
            }
        
        raise ValueError("Could not determine image dimensions")
    
    def _calculate_optimal_region_size(self, service_info: Dict[str, Any], target_size: int) -> int:
        """Calculate the optimal region size based on server constraints and target."""
        max_width = service_info.get('max_width', service_info['width'])
        max_height = service_info.get('max_height', service_info['height'])
        max_area = service_info.get('max_area', service_info['width'] * service_info['height'])
        
        # Start with target size
        optimal_size = target_size
        
        # Constrain by max dimensions
        optimal_size = min(optimal_size, max_width, max_height)
        
        # Constrain by max area (for square regions)
        max_size_from_area = int(math.sqrt(max_area))
        optimal_size = min(optimal_size, max_size_from_area)
        
        # Ensure we don't exceed image dimensions
        optimal_size = min(optimal_size, service_info['width'], service_info['height'])
        
        # Minimum practical size
        optimal_size = max(optimal_size, 512)
        
        return optimal_size
    
    def _generate_high_res_regions(
        self,
        base_url: str,
        width: int,
        height: int,
        region_size: int,
        overlap: int,
        format: str,
        quality: str
    ) -> List[Dict[str, Any]]:
        """Generate high-resolution region coordinates and URLs."""
        regions = []
        
        # Calculate step size (region size minus overlap)
        step_size = region_size - overlap
        
        # Calculate grid
        cols = math.ceil(width / step_size)
        rows = math.ceil(height / step_size)
        
        for row in range(rows):
            for col in range(cols):
                # Calculate region coordinates
                x = col * step_size
                y = row * step_size
                
                # Calculate region dimensions, ensuring we don't exceed image bounds
                w = min(region_size, width - x)
                h = min(region_size, height - y)
                
                # Skip if region is too small to be useful
                if w < 256 or h < 256:
                    continue
                
                # Build IIIF URL - request at maximum available size
                region = f"{x},{y},{w},{h}"
                size = "max"  # Let server decide optimal size
                url = f"{base_url}/{region}/{size}/0/{quality}.{format}"
                
                regions.append({
                    'url': url,
                    'filename': f"region_{col}_{row}.{format}",
                    'column': col,
                    'row': row,
                    'region': {'x': x, 'y': y, 'width': w, 'height': h},
                    'expected_size': {'width': w, 'height': h}
                })
        
        return regions
    
    async def _download_regions(
        self,
        regions: List[Dict[str, Any]],
        output_dir: Path,
        max_concurrent: int
    ) -> Tuple[int, List[str]]:
        """Download regions with progress tracking."""
        semaphore = asyncio.Semaphore(max_concurrent)
        successful_downloads = 0
        errors = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            refresh_per_second=10,
        ) as progress:
            
            task = progress.add_task(f"Downloading {len(regions)} regions", total=len(regions))
            
            async def download_region(region_info):
                nonlocal successful_downloads, errors
                
                async with semaphore:
                    try:
                        file_path = output_dir / region_info['filename']
                        
                        # Skip if already exists
                        if file_path.exists():
                            progress.update(task, advance=1)
                            return True
                        
                        # Use enhanced headers for region downloads too
                        download_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                            "Accept": "image/*,*/*",
                        }
                        if self.headers:
                            download_headers.update(self.headers)
                        
                        timeout = aiohttp.ClientTimeout(total=60)  # Longer timeout for image downloads
                        async with aiohttp.ClientSession(headers=download_headers, timeout=timeout) as session:
                            async with session.get(region_info['url']) as response:
                                if response.status == 200:
                                    async with aiofiles.open(file_path, 'wb') as f:
                                        async for chunk in response.content.iter_chunked(8192):
                                            await f.write(chunk)
                                    successful_downloads += 1
                                    progress.update(task, advance=1)
                                    return True
                                else:
                                    error_msg = f"HTTP {response.status} for {region_info['url']}"
                                    errors.append(error_msg)
                                    progress.update(task, advance=1)
                                    return False
                    
                    except Exception as e:
                        error_msg = f"Error downloading {region_info['url']}: {str(e)}"
                        errors.append(error_msg)
                        progress.update(task, advance=1)
                        return False
            
            # Download all regions concurrently
            tasks = [download_region(region) for region in regions]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return successful_downloads, errors
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Replace problematic characters with underscores
        sanitized = re.sub(r'[^\w\-_.]', '_', filename)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized or "untitled"


# Convenience function for direct usage
async def extract_iiif_regions(
    manifest_url: str,
    target_size: int,
    output_dir: str,
    overlap: int = 64,
    format: str = "jpg",
    quality: str = "default",
    max_concurrent: int = 10,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Extract high-resolution regions from IIIF manifest.
    
    This is a convenience wrapper around the IIIFRegionExtractor class.
    
    Args:
        manifest_url: URL or local path to IIIF manifest
        target_size: Target size for regions in pixels (will be optimized based on server limits)
        output_dir: Directory to save extracted regions
        overlap: Overlap between adjacent regions in pixels
        format: Image format for regions (jpg, png, webp, tif)
        quality: IIIF quality parameter (default, color, gray, bitonal)
        max_concurrent: Maximum concurrent downloads
        headers: Optional HTTP headers
        
    Returns:
        Dictionary with extraction results and metadata
    """
    extractor = IIIFRegionExtractor(headers=headers)
    return await extractor.extract_iiif_regions(
        manifest_url=manifest_url,
        target_size=target_size,
        output_dir=output_dir,
        overlap=overlap,
        format=format,
        quality=quality,
        max_concurrent=max_concurrent
    )


if __name__ == "__main__":
    # Example usage
    import sys
    
    async def main():
        if len(sys.argv) < 4:
            print("Usage: python iiif_tile_extractor.py <manifest_url> <target_size> <output_dir>")
            return
        
        manifest_url = sys.argv[1]
        target_size = int(sys.argv[2])
        output_dir = sys.argv[3]
        
        results = await extract_iiif_regions(
            manifest_url=manifest_url,
            target_size=target_size,
            output_dir=output_dir,
            overlap=64,
            format="jpg",
            max_concurrent=5
        )
        
        print(f"\nExtraction completed!")
        print(f"Results saved to: {output_dir}")
    
    asyncio.run(main())