from pxr import Usd, Tf, UsdUtils, UsdGeom, Gf, Sdf, UsdLux, UsdShade

from math import atan, radians as rad, floor, ceil
import argparse
import os
import sys
from typing import Optional, Tuple

import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class USDLoadingError(Exception):
    """
    Exception raised when USD asset loading encounters warnings or errors.
    
    Attributes:
        asset_path: Path to the asset that failed to load cleanly
        diagnostics: List of diagnostic messages from USD
        fatal_error: Optional fatal exception that occurred during loading
    """
    
    def __init__(self, asset_path: str, diagnostics: list = None, fatal_error: Exception = None):
        self.asset_path = asset_path
        self.diagnostics = diagnostics or []
        self.fatal_error = fatal_error
        
        # Build error message
        message_parts = [f"USD asset failed to load cleanly: {asset_path}"]
        
        if fatal_error:
            message_parts.append(f"Fatal error: {fatal_error}")
        
        if diagnostics:
            message_parts.append(f"Diagnostics ({len(diagnostics)} issues):")
            for i, item in enumerate(diagnostics, 1):
                message_parts.append(f"  {i}. {item.diagnosticCodeString}: {item.commentary}")
        
        super().__init__("\n".join(message_parts))


# =============================================================================
# ANIMATION CONFIGURATION
# =============================================================================

class AnimationConfig:
    """Configuration constants for controlling the animation sequence and timing."""
    
    # Timeline Settings
    FRAME_RATE: int = 60                    # Frames per second
    TOTAL_DURATION: int = 720               # Total animation length in frames (12 seconds at 60fps)
    
    # Asset Movement Animation (traversing bounding box corners)
    ASSET_MOVEMENT_ENABLED: bool = True
    ASSET_MOVEMENT_START: int = 261          # Start after visualizations complete
    ASSET_MOVEMENT_END: int = 340
    ASSET_MOVEMENT_KEYFRAME_INTERVAL: int = 5  # Frames between keyframes
    
    # Light Spinning Animation (renderer-specific lighting)
    LIGHTS_ENABLED: bool = True
    LIGHTS_SPIN_START: int = 181
    LIGHTS_SPIN_END: int = 260
    
    # Renderer-specific light settings
    LIGHTS_OMNIVERSE_ENABLED: bool = True
    LIGHTS_STORM_ENABLED: bool = False
    LIGHTS_OMNIVERSE_INTENSITY: float = 500.0
    LIGHTS_STORM_INTENSITY: float = 1.0
    LIGHTS_ANGLE: float = 15.0
    
    # Asset Spinning Animations
    ASSET_SPINNING_ENABLED: bool = True
    
    # First spin (Z-axis)
    ASSET_SPIN_Z_START: int = 21
    ASSET_SPIN_Z_END: int = 100
    ASSET_SPIN_Z_AXIS: str = 'z'
    
    # Second spin (X-axis)  
    ASSET_SPIN_X_START: int = 101
    ASSET_SPIN_X_END: int = 180
    ASSET_SPIN_X_AXIS: str = 'x'
    
    # Additional spin phases (can be enabled by changing start/end times)
    ASSET_SPIN_Y_START: int = 561
    ASSET_SPIN_Y_END: int = 561  # Disabled by default (start == end)
    ASSET_SPIN_Y_AXIS: str = 'y'
    
    # Visualization Settings
    ORIGIN_VISUALIZATION_ENABLED: bool = True
    ORIGIN_VIZ_SIZE_SCALE: float = 1.0
    ORIGIN_VIZ_START_FRAME: int = 1         # Frame when origin visualization starts
    ORIGIN_VIZ_END_FRAME: int = 10          # Frame when origin visualization ends
    
    SIZE_REFERENCE_ENABLED: bool = True
    SIZE_REF_GRID_SPACING: float = 0.1      # Grid spacing in meters
    SIZE_REF_START_FRAME: int = 11          # Frame when grid visualization starts
    SIZE_REF_END_FRAME: int = 20            # Frame when grid visualization ends
    
    # Camera Settings
    CAMERA_ENABLED: bool = True
    CAMERA_FOV: float = 45.0
    CAMERA_FRAME_FIT: float = 1.5
    
    # Material Override Settings
    MATERIAL_OVERRIDE_ENABLED: bool = True
    MATERIAL_DIFFUSE_COLOR: tuple = (0.18, 0.18, 0.18)     # Light gray diffuse
    MATERIAL_METALLIC: float = 0.0                       # Non-metallic
    MATERIAL_ROUGHNESS: float = 0.4                      # Moderate roughness
    
    @classmethod
    def get_animation_phases(cls) -> list[dict]:
        """
        Get a list of all animation phases in chronological order.
        Useful for debugging and understanding the animation sequence.
        """
        phases = []
        
        if cls.ASSET_MOVEMENT_ENABLED:
            phases.append({
                'name': 'Asset Movement',
                'start': cls.ASSET_MOVEMENT_START,
                'end': cls.ASSET_MOVEMENT_END,
                'description': 'Asset moves through bounding box corners'
            })
        
        if cls.LIGHTS_ENABLED:
            # Build description based on enabled renderers
            enabled_renderers = []
            if cls.LIGHTS_OMNIVERSE_ENABLED:
                enabled_renderers.append(f"Omniverse ({cls.LIGHTS_OMNIVERSE_INTENSITY})")
            if cls.LIGHTS_STORM_ENABLED:
                enabled_renderers.append(f"Storm ({cls.LIGHTS_STORM_INTENSITY})")
            
            renderer_desc = ", ".join(enabled_renderers) if enabled_renderers else "No renderers"
            phases.append({
                'name': 'Light Spinning',
                'start': cls.LIGHTS_SPIN_START,
                'end': cls.LIGHTS_SPIN_END,
                'description': f'Renderer-specific lights rotate: {renderer_desc}'
            })
        
        if cls.ASSET_SPINNING_ENABLED:
            if cls.ASSET_SPIN_Z_START < cls.ASSET_SPIN_Z_END:
                phases.append({
                    'name': f'Asset Spin ({cls.ASSET_SPIN_Z_AXIS.upper()}-axis)',
                    'start': cls.ASSET_SPIN_Z_START,
                    'end': cls.ASSET_SPIN_Z_END,
                    'description': f'Asset rotates 360° around {cls.ASSET_SPIN_Z_AXIS.upper()}-axis'
                })
            
            if cls.ASSET_SPIN_X_START < cls.ASSET_SPIN_X_END:
                phases.append({
                    'name': f'Asset Spin ({cls.ASSET_SPIN_X_AXIS.upper()}-axis)',
                    'start': cls.ASSET_SPIN_X_START,
                    'end': cls.ASSET_SPIN_X_END,
                    'description': f'Asset rotates 360° around {cls.ASSET_SPIN_X_AXIS.upper()}-axis'
                })
                
            if cls.ASSET_SPIN_Y_START < cls.ASSET_SPIN_Y_END:
                phases.append({
                    'name': f'Asset Spin ({cls.ASSET_SPIN_Y_AXIS.upper()}-axis)',
                    'start': cls.ASSET_SPIN_Y_START,
                    'end': cls.ASSET_SPIN_Y_END,
                    'description': f'Asset rotates 360° around {cls.ASSET_SPIN_Y_AXIS.upper()}-axis'
                })
        
        # Add visualization phases
        if cls.ORIGIN_VISUALIZATION_ENABLED:
            duration = cls.ORIGIN_VIZ_END_FRAME - cls.ORIGIN_VIZ_START_FRAME + 1
            phases.append({
                'name': 'Origin Visualization',
                'start': cls.ORIGIN_VIZ_START_FRAME,
                'end': cls.ORIGIN_VIZ_END_FRAME,
                'description': f'Coordinate axes visualization displayed for {duration} frames'
            })
        
        if cls.SIZE_REFERENCE_ENABLED:
            duration = cls.SIZE_REF_END_FRAME - cls.SIZE_REF_START_FRAME + 1
            phases.append({
                'name': 'Size Reference Grid',
                'start': cls.SIZE_REF_START_FRAME,
                'end': cls.SIZE_REF_END_FRAME,
                'description': f'Measurement grid displayed for {duration} frames'
            })
        
        # Add material override info (not time-based but relevant)
        if cls.MATERIAL_OVERRIDE_ENABLED:
            phases.append({
                'name': 'Material Override',
                'start': 0,
                'end': cls.TOTAL_DURATION,
                'description': f'USDPreview Surface applied (strongerThanDescendants)'
            })
        
        # Sort by start time
        phases.sort(key=lambda x: x['start'])
        return phases
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that the configuration makes sense."""
        phases = cls.get_animation_phases()
        
        # Check for overlapping phases
        for i in range(len(phases) - 1):
            current_end = phases[i]['end']
            next_start = phases[i + 1]['start']
            if current_end > next_start:
                logger.warning(f"Animation phases overlap: '{phases[i]['name']}' ends at frame {current_end}, "
                             f"but '{phases[i + 1]['name']}' starts at frame {next_start}")
        
        # Check if any animation goes beyond total duration
        for phase in phases:
            if phase['end'] > cls.TOTAL_DURATION:
                logger.warning(f"Animation phase '{phase['name']}' ends at frame {phase['end']}, "
                             f"which is beyond total duration of {cls.TOTAL_DURATION} frames")
        
        # Validate lighting configuration
        if cls.LIGHTS_ENABLED and not (cls.LIGHTS_OMNIVERSE_ENABLED or cls.LIGHTS_STORM_ENABLED):
            logger.warning("Lights are enabled but no renderer-specific lights are enabled - scene may be dark")
        
        return True


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def loads_without_warnings_or_errors(asset_path: str) -> None:
    """
    Test whether a USD asset loads without emitting warnings or errors.
    Uses USD's CoalescingDiagnosticDelegate to capture all diagnostic
    messages (warnings and errors) that occur during stage loading.
    
    Runtime Testing: AA.002 - "The asset loads into a runtime environment without 
    errors or warnings related to unsupported schemas or invalid data."
    Note: This is not strictly required as part of the Minimal Placeable Visual 
    feature, but serves as a good baseline test for all runtime testing.

    Note that USDImaging diagnostics will not be captured when USDImaging
    is not in use, for example when using USD without a renderer.
    
    Args:
        asset_path (str): Path to the USD asset file to be tested.
    
    Returns:
        None: Function returns successfully if asset loads cleanly.
    
    Raises:
        USDLoadingError: Raised when any warnings, errors, or fatal exceptions 
            occur during stage loading. The exception contains detailed information
            about all diagnostic messages encountered.
        FileNotFoundError: If the asset file does not exist.
    
    Example:
        >>> try:
        ...     loads_without_warnings_or_errors("./test_asset.usda")
        ...     print("Asset passed validation")
        ... except USDLoadingError as e:
        ...     print(f"Asset failed validation: {e}")
        ... except FileNotFoundError:
        ...     print("Asset file not found")
    
    Note:
        This function raises exceptions with detailed diagnostic information
        instead of logging and returning boolean values, making it easier to
        integrate into automated validation workflows.
    """

    delegate = UsdUtils.CoalescingDiagnosticDelegate()
    
    try:
        stage = Usd.Stage.Open(asset_path)
    except Exception as e:
        # Collect any diagnostics that might have been generated before the fatal error
        items = delegate.TakeUncoalescedDiagnostics()
        raise USDLoadingError(asset_path, diagnostics=items, fatal_error=e)

    items = delegate.TakeUncoalescedDiagnostics()

    if items:
        # Raise exception with all collected diagnostics
        raise USDLoadingError(asset_path, diagnostics=items)

    logger.info(f"Stage loaded without warnings or errors: {asset_path}")
    return None




class Camera:
    """
    A camera helper class for framing and positioning a USD camera to view scene geometry.
    
    This class automatically positions and orients a camera to frame a given bounding box,
    similar to viewport "frame all" functionality in 3D applications.

    Logic is copied from usdview's freeCamera module:
    https://github.com/PixarAnimationStudios/OpenUSD/blob/dev/pxr/usdImaging/usdviewq/freeCamera.py

    
    TODO: Clipping planes
    """
    
    # DEFAULTS
    CAMERA_PATH: str = '/CAMERA'
    DEFAULT_NEAR: float = 0.1
    DEFAULT_FAR: float = 2000000
    
    def __init__(self, camera_prim: UsdGeom.Camera, isZUp: bool = False) -> None:
        """
        Initialize the camera with rotation and coordinate system setup.
        
        Args:
            camera_prim: USD camera prim to configure
            isZUp (bool): Whether the stage uses Z-up coordinate system
        """
        # Initial rotation values for camera orientation
        self._rotPsi: float = 0
        self._rotPhi: float = 22.5  # Slight angle to avoid dead-on view
        self._rotTheta: float = 22.5

        self.camera_prim: UsdGeom.Camera = camera_prim
        self._camera: Gf.Camera = Gf.Camera()

        # Set up coordinate system transformation matrices
        if isZUp:
            self._YZUpMatrix: Gf.Matrix4d = Gf.Matrix4d().SetRotate(
                Gf.Rotation(Gf.Vec3d.XAxis(), -90))
            self._YZUpInvMatrix: Gf.Matrix4d = self._YZUpMatrix.GetInverse()
        else:
            self._YZUpMatrix: Gf.Matrix4d = Gf.Matrix4d(1.0)
            self._YZUpInvMatrix: Gf.Matrix4d = Gf.Matrix4d(1.0)

    def frame(self, bbox: Gf.BBox3d) -> Gf.Matrix4d:
        """
        Frame the camera to view the given bounding box.
        
        Args:
            bbox: A Gf.BBox3d representing the geometry to frame
            
        Returns:
            Gf.Matrix4d: The camera transform matrix
        """
        # Calculate framing parameters
        self.center: Gf.Vec3d = bbox.ComputeCentroid()
        selRange: Gf.Range3d = bbox.ComputeAlignedRange()
        self._selSize: float = max(*selRange.GetSize())

        # Calculate camera distance based on field of view
        fov = AnimationConfig.CAMERA_FOV
        frame_fit = AnimationConfig.CAMERA_FRAME_FIT
        halfFov: float = fov * 0.5 or 0.5  # Prevent division by zero
        lengthToFit: float = self._selSize * frame_fit * 0.5
        self.dist: float = lengthToFit / atan(rad(halfFov))

        
        # Very small objects that fill out their bounding boxes (like cubes)
        # may well pierce our 1 unit default near-clipping plane. Make sure
        # that doesn't happen.
        if self.dist < Camera.DEFAULT_NEAR + self._selSize * 0.5:
            self.dist = Camera.DEFAULT_NEAR + lengthToFit

        self._camera.clippingRange = Gf.Range1f(self.DEFAULT_NEAR, self.DEFAULT_FAR)

        
        # Apply the calculated transform
        return self._pushToCameraTransform()

    
    def _pushToCameraTransform(self) -> Gf.Matrix4d:
        """
        Updates the camera's transform matrix, that is, the matrix that brings
        the camera to the origin, with the camera view pointing down:
           +Y if this is a Zup camera, or
           -Z if this is a Yup camera .
           
        Returns:
            Gf.Matrix4d: The camera transform matrix
        """
        
        def RotMatrix(vec: Gf.Vec3d, angle: float) -> Gf.Matrix4d:
            return Gf.Matrix4d(1.0).SetRotate(Gf.Rotation(vec, angle))
        
        # Build the camera transform matrix
        self._camera.transform = (
            Gf.Matrix4d().SetTranslate(Gf.Vec3d.ZAxis() * self.dist) *
            RotMatrix(Gf.Vec3d.ZAxis(), -self._rotPsi) *
            RotMatrix(Gf.Vec3d.XAxis(), -self._rotPhi) *
            RotMatrix(Gf.Vec3d.YAxis(), -self._rotTheta) *
            self._YZUpInvMatrix *
            Gf.Matrix4d().SetTranslate(self.center))

        # Set camera properties        
        self._camera.SetPerspectiveFromAspectRatioAndFieldOfView(
            self._camera.aspectRatio, AnimationConfig.CAMERA_FOV, Gf.Camera.FOVVertical
        )

        # Set camera properties
        self._camera.focusDistance = self.dist
        self.camera_prim.SetFromCamera(self._camera)

        return self._camera.transform


def _compute_stage_bounding_box(stage: Usd.Stage, default_prim_only: bool = True) -> Gf.BBox3d:
    """
    Compute the bounding box of boundable prims in the stage.
    
    Args:
        stage: The USD stage to compute bounding box for
        default_prim_only: If True, only traverse the default prim hierarchy.
                          If False, traverse the entire stage.
    
    Returns:
        Gf.BBox3d: Combined bounding box of all boundable prims

    Raises:
        ValueError: If no default prim is found and default_prim_only is True
    """
    bbox_cache: UsdGeom.BBoxCache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render', 'proxy'])
    total_bbox: Gf.BBox3d = Gf.BBox3d()  

    # Determine the traversal approach
    if default_prim_only:
        root_prim: Usd.Prim = stage.GetDefaultPrim()
        if not root_prim.IsValid():
            raise ValueError("No default prim found, cannot compute bounding box")
        
        # Traverse only the default prim and its descendants
        base_pred = Usd.PrimDefaultPredicate
        inst_pred = Usd.TraverseInstanceProxies(base_pred)

        for prim in Usd.PrimRange(root_prim, predicate=inst_pred):
            if prim.IsA(UsdGeom.Boundable):
                bbox: Gf.BBox3d = bbox_cache.ComputeWorldBound(prim)
                total_bbox = Gf.BBox3d.Combine(total_bbox, bbox)
    else:
        # Traverse the entire stage
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Boundable):
                bbox: Gf.BBox3d = bbox_cache.ComputeWorldBound(prim)
                total_bbox = Gf.BBox3d.Combine(total_bbox, bbox)

    return total_bbox



def create_and_frame_camera(stage: Usd.Stage, asset_up_axis: str, asset_bbox: Gf.BBox3d) -> Usd.Stage:
    """
    Create a camera and frame it to the provided bounding box.

    Runtime Testing: VG.001, VG.002 - "The asset's geometry is visible and can be 
    automatically framed by the viewport's perspective camera, indicating a valid 
    and computable bounding box."

    Args:
        stage (Usd.Stage): The stage to add the camera to
        asset_up_axis: The up axis of the asset stage
        asset_bbox: Pre-computed bounding box of the asset
    
    Returns:
        Usd.Stage: The stage containing the framed camera
    """    
    
    # Use the provided bounding box
    if asset_bbox is None or asset_bbox.GetRange().IsEmpty():
        raise AssertionError("Provided bounding box is empty or None, cannot frame camera")

    # Remove existing camera if it exists
    existing_prim: Usd.Prim = stage.GetPrimAtPath(Camera.CAMERA_PATH)
    if existing_prim.IsValid():
        stage.RemovePrim(Camera.CAMERA_PATH)

    # Create camera prim
    camera_prim: UsdGeom.Camera = UsdGeom.Camera.Define(stage, Camera.CAMERA_PATH)
    if not camera_prim.GetPrim().IsValid():
        raise RuntimeError(f"Failed to create camera at {Camera.CAMERA_PATH}")

    # Configure camera based on provided up axis
    isZUp: bool = asset_up_axis == UsdGeom.Tokens.z
    logger.info(f"Asset stage is ZUp: {isZUp}")
    camera: Camera = Camera(camera_prim, isZUp)
    camera_matrix: Gf.Matrix4d = camera.frame(asset_bbox)
    logger.info(f"Created camera at {Camera.CAMERA_PATH} with transform: {camera_matrix}")
    
    
    return stage


def move_asset(stage: Usd.Stage, asset_bbox: Gf.BBox3d) -> Usd.Stage:
    """
    Find the default prim of the stage and move the asset a certain distance in each axis over a certain time.
    Uses the current edit target layer.

    Runtime Testing: HI.001, HI.003 - "The asset can be positioned, rotated and scaled 
    by setting the translate, rotate and scale attributes on the root prim." Tests that 
    the asset has a single root prim that is Xformable and can be transformed.
    """
    
    if not AnimationConfig.ASSET_MOVEMENT_ENABLED:
        logger.info("Asset movement animation disabled, skipping")
        return stage

    # Find the default prim of the stage
    default_prim: Usd.Prim = stage.GetDefaultPrim()
    logger.info(f"Default prim: {default_prim} on stage: {stage}")
    if default_prim is None:
        raise ValueError("Default prim is not set")
    
    xform_api: UsdGeom.XformCommonAPI = UsdGeom.XformCommonAPI(default_prim)
    if not xform_api:
        raise ValueError(f"Can not initialize xform common api on the default prim {default_prim} - wrong type ?")

    # Use the assets bounding box to determine how much the asset should move
    bbox_range: Gf.Range3d = asset_bbox.GetRange()
    min_point: Gf.Vec3d = bbox_range.GetMin()
    max_point: Gf.Vec3d = bbox_range.GetMax()
    
    # Generate keyframes dynamically based on configuration
    start_frame = AnimationConfig.ASSET_MOVEMENT_START
    end_frame = AnimationConfig.ASSET_MOVEMENT_END
    interval = AnimationConfig.ASSET_MOVEMENT_KEYFRAME_INTERVAL
    
    # Define the 8 corners of the bounding box + origin
    corners = [
        (0, 0, 0),      # Origin
        (min_point[0], min_point[1], min_point[2]),      # Bottom-back-left
        (max_point[0], min_point[1], min_point[2]),      # Bottom-back-right
        (max_point[0], max_point[1], min_point[2]),     # Bottom-front-right
        (min_point[0], max_point[1], min_point[2]),     # Bottom-front-left
        (min_point[0], min_point[1], max_point[2]),     # Top-back-left
        (max_point[0], min_point[1], max_point[2]),     # Top-back-right
        (max_point[0], max_point[1], max_point[2]),     # Top-front-right
        (min_point[0], max_point[1], max_point[2]),     # Top-front-left
        (0, 0, 0)      # Return to origin
    ]
    
    # Create keyframes with configurable timing
    keyframes: dict[int, Tuple[float, float, float]] = {}
    for i, corner in enumerate(corners):
        frame = start_frame + (i * interval)
        if frame <= end_frame:
            keyframes[frame] = corner
        else:
            # If we run out of time, put the last keyframe at the end
            keyframes[end_frame] = corner
            break

    for frame, (x, y, z) in keyframes.items():
        xform_api.SetTranslate(Gf.Vec3d(x, y, z), frame)

    logger.info(f"Created asset movement animation from frame {start_frame} to {end_frame} with {len(keyframes)} keyframes")
    return stage


def setup_test_stage(asset_path: str, test_stage_path: str) -> Usd.Stage:
    """
    Create a test stage with proper coordinate system and reference the asset.

    Runtime Testing Requirements:
    - UN.001, UN.006: Z-up coordinate system for correct "up" direction
    - UN.002, UN.007: metersPerUnit=1.0 for correct real-world physical scale  
    - HI.004: Asset can be referenced without specifying prim path (default prim)
    """
    stage: Usd.Stage = Usd.Stage.CreateNew(test_stage_path)

    asset_prim: Usd.Prim = stage.DefinePrim('/ASSET', 'Xform')
    if not asset_prim.IsValid():
        raise RuntimeError(f"Failed to create asset prim at /ASSET")

    UsdGeom.SetStageMetersPerUnit(stage, 1.0)  # UN.002: Real-world scale
    stage.SetTimeCodesPerSecond(AnimationConfig.FRAME_RATE)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(AnimationConfig.TOTAL_DURATION)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)  # UN.001: Z-up coordinate system
    stage.SetDefaultPrim(asset_prim)

    asset_prim.GetPrim().GetReferences().AddReference(asset_path)  # HI.001: Reference without prim path

    stage.Save()

    return stage


def spin_lights(stage: Usd.Stage, asset_up_axis: str) -> Usd.Stage:
    """
    Create renderer-specific distant lights and spin them in the scene.
    Creates separate lights optimized for different renderers (Omniverse, Storm).

    Runtime Testing: VG.MESH.001, VG.027 - "The asset's surfaces render correctly 
    without unintended holes or gaps." Light rotation reveals geometry issues and 
    validates that surface normals are properly authored for correct shading.
    """
    
    if not AnimationConfig.LIGHTS_ENABLED:
        logger.info("Light spinning animation disabled, skipping")
        return stage
    
    # Create lights group
    lights_prim: UsdGeom.Xform = UsdGeom.Xform.Define(stage, '/LIGHTS')
    lights_created = 0
    
    def add_renderer_light(renderer_name: str, intensity: float) -> UsdLux.DistantLight:
        """Helper function to create a renderer-specific distant light."""
        path = f'/LIGHTS/{renderer_name}_Light'
        light: UsdLux.DistantLight = UsdLux.DistantLight.Define(stage, path)
        
        # Set intensity and angle
        light.CreateIntensityAttr(intensity)
        light.CreateAngleAttr(AnimationConfig.LIGHTS_ANGLE)
        
        # Position light at 45° elevation, 30° azimuth for good asset illumination
        light_xform: UsdGeom.XformCommonAPI = UsdGeom.XformCommonAPI(light)
        light_xform.SetRotate(Gf.Vec3f(45, 30, 0))
        
        logger.info(f"Created {renderer_name} light with intensity {intensity}")
        return light
    
    # Create Omniverse-specific light
    if AnimationConfig.LIGHTS_OMNIVERSE_ENABLED:
        add_renderer_light('Omniverse', AnimationConfig.LIGHTS_OMNIVERSE_INTENSITY)
        lights_created += 1
    
    # Create Storm-specific light  
    if AnimationConfig.LIGHTS_STORM_ENABLED:
        add_renderer_light('Storm', AnimationConfig.LIGHTS_STORM_INTENSITY)
        lights_created += 1
    
    if lights_created == 0:
        logger.warning("No renderer lights enabled - scene may be dark")
    else:
        logger.info(f"Created {lights_created} renderer-specific light(s)")


    # Animate the lights with the xformcommonapi
    xform_api: UsdGeom.XformCommonAPI = UsdGeom.XformCommonAPI(lights_prim)
    
    start_frame = AnimationConfig.LIGHTS_SPIN_START
    end_frame = AnimationConfig.LIGHTS_SPIN_END
    
    isZUp: bool = asset_up_axis == UsdGeom.Tokens.z
    if isZUp:
        xform_api.SetRotate(Gf.Vec3f(0, 0, 0), time=Usd.TimeCode(start_frame))
        xform_api.SetRotate(Gf.Vec3f(0, 0, 360), time=Usd.TimeCode(end_frame))
    else:
        xform_api.SetRotate(Gf.Vec3f(0, 0, 0), time=Usd.TimeCode(start_frame))
        xform_api.SetRotate(Gf.Vec3f(0, 360, 0), time=Usd.TimeCode(end_frame))

    stage.Save()
    
    logger.info(f"Created light spinning animation from frame {start_frame} to {end_frame}")
    return stage

def spin_asset(stage: Usd.Stage, axis: str = 'z', start_time: int = 300, end_time: int = 480) -> Usd.Stage:
    """
    Spin the asset in the scene around a specified axis.
    Uses the current edit target layer.

    Runtime Testing: 
    - VG.027, VG.028, VG.029: Verifies proper normal orientation, surface shading,
      and correct winding order from all angles as the asset rotates
    - VG.025: Tests asset rotation around specified pivot point for articulation
    
    Args:
        stage: The USD stage containing the asset
        axis: The axis to spin around ('x', 'y', or 'z')
        start_time: The start time code for the animation
        end_time: The end time code for the animation
    """
    
    if not AnimationConfig.ASSET_SPINNING_ENABLED:
        logger.info("Asset spinning animation disabled, skipping")
        return stage
        
    if start_time >= end_time:
        logger.info(f"Asset spin animation on {axis.upper()}-axis disabled (start_time >= end_time)")
        return stage
    
    # Get the asset prim
    asset_prim: Usd.Prim = stage.GetPrimAtPath('/ASSET')
    if not asset_prim.IsValid():
        raise RuntimeError(f"Failed to get asset prim at /ASSET")
    
    # Get the xform common api
    xform_api: UsdGeom.XformCommonAPI = UsdGeom.XformCommonAPI(asset_prim)
    
    # Set up rotation vectors based on axis
    if axis.lower() == 'x':
        start_rotation: Gf.Vec3f = Gf.Vec3f(0, 0, 0)
        end_rotation: Gf.Vec3f = Gf.Vec3f(360, 0, 0)
    elif axis.lower() == 'y':
        start_rotation = Gf.Vec3f(0, 0, 0)
        end_rotation = Gf.Vec3f(0, 360, 0)
    elif axis.lower() == 'z':
        start_rotation = Gf.Vec3f(0, 0, 0)
        end_rotation = Gf.Vec3f(0, 0, 360)
    else:
        raise ValueError(f"Invalid axis '{axis}'. Must be 'x', 'y', or 'z'")
    
    # Set keyframes for rotation
    xform_api.SetTranslate(Gf.Vec3d(0, 0, 0), time=Usd.TimeCode(start_time))
    xform_api.SetRotate(start_rotation, time=Usd.TimeCode(start_time))
    xform_api.SetRotate(end_rotation, time=Usd.TimeCode(end_time))
    
    logger.info(f"Created asset spinning animation on {axis.upper()}-axis from frame {start_time} to {end_time}")
    return stage

def create_origin_visualization(stage: Usd.Stage, asset_up_axis: str, asset_bbox: Gf.BBox3d, size: float = 1.0) -> Usd.Stage:
    """
    Runtime Testing: UN.001, UN.006 - "When referenced into a stage with upAxis 
    set to 'Z', the asset appears with the correct 'up' direction."
    
    Create three colored cylinders at the origin to visualize the coordinate axes.
    The cylinder length is based on the provided bounding box.
    The visualization is visible during the configured frame range.

    
    Args:
        stage: The USD stage to add the visualization to
        asset_up_axis: The up axis of the asset stage
        asset_bbox: Pre-computed bounding box of the asset
        size: Scale factor for the size of the cylinders
    
    Returns:
        Usd.Stage: The stage with origin visualization added
    """
    
    if not AnimationConfig.ORIGIN_VISUALIZATION_ENABLED:
        logger.info("Origin visualization disabled, skipping")
        return stage
    
    # Use configured size scale
    size = AnimationConfig.ORIGIN_VIZ_SIZE_SCALE
    
    # Use the provided bounding box
    if asset_bbox is None or asset_bbox.GetRange().IsEmpty():
        raise RuntimeError("Provided bounding box is empty or None, using default size")
        height: float = 2.0 * size
    else:
        bbox_range: Gf.Range3d = asset_bbox.GetRange()
        
        # Use the largest dimension of the bounding box
        bbox_size: Gf.Vec3d = bbox_range.GetSize()
        max_dimension: float = max(bbox_size[0], bbox_size[1], bbox_size[2])
        
        # Apply minimum size constraint and scale factor
        height = max(max_dimension * size, 1.0 * size)
        
        logger.info(f"Asset bounding box size: {bbox_size}, using cylinder height: {height}")
    
    # Create a group for the origin visualization
    origin_group: UsdGeom.Xform = UsdGeom.Xform.Define(stage, '/ORIGIN_VIZ')
    
    # Cylinder dimensions
    radius: float = 0.005 * height
    
    # X-axis cylinder (Red)
    x_cylinder: UsdGeom.Cylinder = UsdGeom.Cylinder.Define(stage, '/ORIGIN_VIZ/X_AXIS')
    x_cylinder.CreateRadiusAttr(radius)
    x_cylinder.CreateHeightAttr(height)
    x_cylinder.CreateAxisAttr('X')  # Orient along X-axis
    x_cylinder.CreateDisplayColorAttr([(1.0, 0.0, 0.0)])  # Red
    
    # Y-axis cylinder (Green)
    y_cylinder: UsdGeom.Cylinder = UsdGeom.Cylinder.Define(stage, '/ORIGIN_VIZ/Y_AXIS')
    y_cylinder.CreateRadiusAttr(radius)
    y_cylinder.CreateHeightAttr(height)
    y_cylinder.CreateAxisAttr('Y')  # Orient along Y-axis
    y_cylinder.CreateDisplayColorAttr([(0.0, 1.0, 0.0)])  # Green
    
    # Z-axis cylinder (Blue)
    z_cylinder: UsdGeom.Cylinder = UsdGeom.Cylinder.Define(stage, '/ORIGIN_VIZ/Z_AXIS')
    z_cylinder.CreateRadiusAttr(radius)
    z_cylinder.CreateHeightAttr(height)
    z_cylinder.CreateAxisAttr('Z')  # Orient along Z-axis
    z_cylinder.CreateDisplayColorAttr([(0.0, 0.0, 1.0)])  # Blue
    
    # Animate visibility: visible for the configured frame range
    start_frame = AnimationConfig.ORIGIN_VIZ_START_FRAME
    end_frame = AnimationConfig.ORIGIN_VIZ_END_FRAME
    origin_group.CreateVisibilityAttr()
    
    # Set visibility keyframes
    if start_frame > 0:
        origin_group.GetVisibilityAttr().Set(UsdGeom.Tokens.invisible, time=Usd.TimeCode(0))
    origin_group.GetVisibilityAttr().Set(UsdGeom.Tokens.inherited, time=Usd.TimeCode(start_frame))
    origin_group.GetVisibilityAttr().Set(UsdGeom.Tokens.invisible, time=Usd.TimeCode(end_frame + 1))
    
    logger.info(f"Created origin visualization with cylinders at /ORIGIN_VIZ, height: {height}, visible frames {start_frame}-{end_frame}")
    
    return stage

def create_size_reference_visualization(stage: Usd.Stage, asset_up_axis: str, asset_bbox: Gf.BBox3d) -> Usd.Stage:
    """
    Runtime Testing: UN.002, UN.007 - "When referenced into a stage with 
    metersPerUnit set to 1.0, the asset appears at its correct, real-world 
    physical scale (e.g., a 2-meter tall object is 2 units high in the scene)."
    
    Create a grid of cylinders spaced at configurable intervals (default 10cm).

    
    Args:
        stage: The USD stage to add the visualization to
        asset_up_axis: The up axis of the asset stage
        asset_bbox: Pre-computed bounding box of the asset
        size: Scale factor for positioning
    
    Returns:
        Usd.Stage: The stage with size reference visualization added
    """
    
    if not AnimationConfig.SIZE_REFERENCE_ENABLED:
        logger.info("Size reference visualization disabled, skipping")
        return stage
    
    # Use the provided bounding box
    if asset_bbox is None or asset_bbox.GetRange().IsEmpty():
        raise RuntimeError("Provided bounding box is empty or None, cannot create size reference")
        return stage
    
    bbox_range: Gf.Range3d = asset_bbox.GetRange()
    bbox_max: Gf.Vec3d = bbox_range.GetMax()
    bbox_min: Gf.Vec3d = bbox_range.GetMin()
    
    # Create a group for the size reference visualization
    size_ref_group: UsdGeom.Xform = UsdGeom.Xform.Define(stage, '/SIZE_REFERENCE')
    
    # Define measurement units and their properties
    units: list[dict[str, any]] = [
        {'name': 'km', 'size': 1000.0, 'color': (1.0, 1.0, 0.0), 'label': '1km'},   # Light yellow
        {'name': 'm', 'size': 1.0, 'color': (0.0, 0.0, 1.0), 'label': '1m'},        # Light blue
        {'name': 'cm', 'size': 0.01, 'color': (0.0, 1.0, 0.0), 'label': '1cm'},     # Light green
        {'name': 'mm', 'size': 0.001, 'color': (1.0, 0.0, 0.0), 'label': '1mm'},    # Light red
    ]
    
    # Position squares to the right of the bounding box
    # base_x_offset = bbox_max[0] + (bbox_max[0] - bbox_min[0]) * 0.2
    # y_spacing = (bbox_max[1] - bbox_min[1]) * 0.25
    # base_y = bbox_min[1] + (bbox_max[1] - bbox_min[1]) * 0.5
    
    # Draw a grid that extends from origin to the edge of the asset's bounding box
    bbox_range = asset_bbox.GetRange()
    bbox_max = bbox_range.GetMax()
    bbox_min = bbox_range.GetMin()
    
    # Use configured grid spacing
    grid_spacing: float = AnimationConfig.SIZE_REF_GRID_SPACING
    
    # Calculate grid extents to cover bbox and always include origin
    grid_min_x: float = min(bbox_min[0], 0)
    grid_max_x: float = max(bbox_max[0], 0)
    grid_min_y: float = min(bbox_min[1], 0)
    grid_max_y: float = max(bbox_max[1], 0)
    grid_min_z: float = min(bbox_min[2], 0)
    grid_max_z: float = max(bbox_max[2], 0)
    
    # Calculate grid line positions - use floor/ceil to ensure complete coverage
    x_start: int = int(floor(grid_min_x / grid_spacing))
    x_end: int = int(ceil(grid_max_x / grid_spacing))
    y_start: int = int(floor(grid_min_y / grid_spacing))
    y_end: int = int(ceil(grid_max_y / grid_spacing))
    z_start: int = int(floor(grid_min_z / grid_spacing))
    z_end: int = int(ceil(grid_max_z / grid_spacing))
    
    # Calculate actual grid extents (where the first and last grid lines are positioned)
    actual_x_min: float = x_start * grid_spacing
    actual_x_max: float = x_end * grid_spacing
    actual_y_min: float = y_start * grid_spacing
    actual_y_max: float = y_end * grid_spacing
    actual_z_min: float = z_start * grid_spacing
    actual_z_max: float = z_end * grid_spacing
    
    # Create grid lines in X direction (parallel to X-axis, spaced along Z)
    for i in range(z_start, z_end + 1):
        z_pos: float = i * grid_spacing
        # Thicker lines at integer meters
        is_meter_line: bool = abs(z_pos % 1.0) < 0.01  # Account for floating point precision
        radius: float = 0.0025 if is_meter_line else 0.00125 
        
        # Create valid USD path name (handle negative indices)
        path_suffix: str = f"N{abs(i)}" if i < 0 else str(i)
        cylinder: str = f'/SIZE_REFERENCE/GRID_X_{path_suffix}'
        cylinder_prim: UsdGeom.Cylinder = UsdGeom.Cylinder.Define(stage, cylinder)
        cylinder_prim.CreateRadiusAttr(radius)
        cylinder_prim.CreateHeightAttr(actual_x_max - actual_x_min)
        cylinder_prim.CreateAxisAttr('X')
        cylinder_prim.CreateDisplayColorAttr([(0.6, 0.6, 0.6)])  # Light gray
        xform_api: UsdGeom.XformCommonAPI = UsdGeom.XformCommonAPI(cylinder_prim)
        xform_api.SetTranslate(Gf.Vec3d((actual_x_min + actual_x_max) / 2, 0, z_pos))
    
    # Create grid lines in Z direction (parallel to Z-axis, spaced along X)
    for i in range(x_start, x_end + 1):
        x_pos: float = i * grid_spacing
        # Thicker lines at integer meters
        is_meter_line = abs(x_pos % 1.0) < 0.01  # Account for floating point precision
        radius = 0.0025 if is_meter_line else 0.00125 
        
        # Create valid USD path name (handle negative indices)
        path_suffix = f"N{abs(i)}" if i < 0 else str(i)
        cylinder = f'/SIZE_REFERENCE/GRID_Z_{path_suffix}'
        cylinder_prim = UsdGeom.Cylinder.Define(stage, cylinder)
        cylinder_prim.CreateRadiusAttr(radius)
        cylinder_prim.CreateHeightAttr(actual_z_max - actual_z_min)
        cylinder_prim.CreateAxisAttr('Z')
        cylinder_prim.CreateDisplayColorAttr([(0.6, 0.6, 0.6)])  # Light gray
        xform_api = UsdGeom.XformCommonAPI(cylinder_prim)
        xform_api.SetTranslate(Gf.Vec3d(x_pos, 0, (actual_z_min + actual_z_max) / 2))
    
    # Create grid lines in X direction for X/Y plane (parallel to X-axis, spaced along Y)
    # These lines extend the full X grid range to connect with Y-direction lines
    for i in range(y_start, y_end + 1):
        y_pos: float = i * grid_spacing
        # Thicker lines at integer meters
        is_meter_line = abs(y_pos % 1.0) < 0.01  # Account for floating point precision
        radius = 0.0025 if is_meter_line else 0.00125 
        
        # Create valid USD path name (handle negative indices)
        path_suffix = f"N{abs(i)}" if i < 0 else str(i)
        cylinder = f'/SIZE_REFERENCE/GRID_XY_X_{path_suffix}'
        cylinder_prim = UsdGeom.Cylinder.Define(stage, cylinder)
        cylinder_prim.CreateRadiusAttr(radius)
        cylinder_prim.CreateHeightAttr(actual_x_max - actual_x_min)
        cylinder_prim.CreateAxisAttr('X')
        cylinder_prim.CreateDisplayColorAttr([(0.5, 0.5, 0.5)])  # Medium gray
        xform_api = UsdGeom.XformCommonAPI(cylinder_prim)
        xform_api.SetTranslate(Gf.Vec3d((actual_x_min + actual_x_max) / 2, y_pos, 0))
    
    # Create grid lines in Y direction for X/Y plane (parallel to Y-axis, spaced along X)
    # These lines extend the full Y grid range to connect with X-direction lines
    for i in range(x_start, x_end + 1):
        x_pos = i * grid_spacing
        # Thicker lines at integer meters
        is_meter_line = abs(x_pos % 1.0) < 0.01  # Account for floating point precision
        radius = 0.0025 if is_meter_line else 0.00125  # Reduced by 50%
        
        # Create valid USD path name (handle negative indices)
        path_suffix = f"N{abs(i)}" if i < 0 else str(i)
        cylinder = f'/SIZE_REFERENCE/GRID_XY_Y_{path_suffix}'
        cylinder_prim = UsdGeom.Cylinder.Define(stage, cylinder)
        cylinder_prim.CreateRadiusAttr(radius)
        cylinder_prim.CreateHeightAttr(actual_y_max - actual_y_min)
        cylinder_prim.CreateAxisAttr('Y')
        cylinder_prim.CreateDisplayColorAttr([(0.5, 0.5, 0.5)])  # Medium gray
        xform_api = UsdGeom.XformCommonAPI(cylinder_prim)
        xform_api.SetTranslate(Gf.Vec3d(x_pos, (actual_y_min + actual_y_max) / 2, 0))
    
    # Create grid lines in Y direction for Y/Z plane (parallel to Y-axis, spaced along Z)
    # These lines extend the full Y grid range to connect with Z-direction lines
    for i in range(z_start, z_end + 1):
        z_pos: float = i * grid_spacing
        # Thicker lines at integer meters
        is_meter_line = abs(z_pos % 1.0) < 0.01  # Account for floating point precision
        radius = 0.0025 if is_meter_line else 0.00125  # Reduced by 50%
        
        # Create valid USD path name (handle negative indices)
        path_suffix = f"N{abs(i)}" if i < 0 else str(i)
        cylinder = f'/SIZE_REFERENCE/GRID_YZ_Y_{path_suffix}'
        cylinder_prim = UsdGeom.Cylinder.Define(stage, cylinder)
        cylinder_prim.CreateRadiusAttr(radius)
        cylinder_prim.CreateHeightAttr(actual_y_max - actual_y_min)
        cylinder_prim.CreateAxisAttr('Y')
        cylinder_prim.CreateDisplayColorAttr([(0.4, 0.4, 0.4)])  # Dark gray
        xform_api = UsdGeom.XformCommonAPI(cylinder_prim)
        xform_api.SetTranslate(Gf.Vec3d(0, (actual_y_min + actual_y_max) / 2, z_pos))
    
    # Create grid lines in Z direction for Y/Z plane (parallel to Z-axis, spaced along Y)
    # These lines extend the full Z grid range to connect with Y-direction lines
    for i in range(y_start, y_end + 1):
        y_pos: float = i * grid_spacing
        # Thicker lines at integer meters
        is_meter_line = abs(y_pos % 1.0) < 0.01  # Account for floating point precision
        radius = 0.0025 if is_meter_line else 0.00125  # Reduced by 50%
        
        # Create valid USD path name (handle negative indices)
        path_suffix = f"N{abs(i)}" if i < 0 else str(i)
        cylinder = f'/SIZE_REFERENCE/GRID_YZ_Z_{path_suffix}'
        cylinder_prim = UsdGeom.Cylinder.Define(stage, cylinder)
        cylinder_prim.CreateRadiusAttr(radius)
        cylinder_prim.CreateHeightAttr(actual_z_max - actual_z_min)
        cylinder_prim.CreateAxisAttr('Z')
        cylinder_prim.CreateDisplayColorAttr([(0.4, 0.4, 0.4)])  # Dark gray
        xform_api = UsdGeom.XformCommonAPI(cylinder_prim)
        xform_api.SetTranslate(Gf.Vec3d(0, y_pos, (actual_z_min + actual_z_max) / 2))
        
    
    # Add a text label group (as comment for now since USD text is complex)
    # In a real implementation, you might want to add UsdGeom.Points with labels
    
    # Animate visibility: visible for the configured frame range
    start_frame = AnimationConfig.SIZE_REF_START_FRAME
    end_frame = AnimationConfig.SIZE_REF_END_FRAME
    size_ref_group.CreateVisibilityAttr()
    
    # Set visibility keyframes
    if start_frame > 0:
        size_ref_group.GetVisibilityAttr().Set(UsdGeom.Tokens.invisible, time=Usd.TimeCode(0))
    size_ref_group.GetVisibilityAttr().Set(UsdGeom.Tokens.inherited, time=Usd.TimeCode(start_frame))
    size_ref_group.GetVisibilityAttr().Set(UsdGeom.Tokens.invisible, time=Usd.TimeCode(end_frame + 1))
    
    logger.info(f"Created size reference visualization with grid spacing {grid_spacing}m, visible frames {start_frame}-{end_frame}")
    
    return stage


def apply_material_override(stage: Usd.Stage) -> Usd.Stage:
    """
    Create a USDPreview Surface material and bind it to the asset root prim
    with "strongerThanDescendants" binding to override any existing materials.
    
    Args:
        stage: The USD stage to add the material to
    
    Returns:
        Usd.Stage: The stage with material override applied
    """
    
    if not AnimationConfig.MATERIAL_OVERRIDE_ENABLED:
        logger.info("Material override disabled, skipping")
        return stage
    
    # Create material
    material_path = '/MATERIALS/OverrideMaterial'
    material: UsdShade.Material = UsdShade.Material.Define(stage, material_path)
    
    # Create UsdPreviewSurface shader
    surface_shader_path = f'{material_path}/PreviewSurface'
    surface_shader: UsdShade.Shader = UsdShade.Shader.Define(stage, surface_shader_path)
    surface_shader.CreateIdAttr("UsdPreviewSurface")
    
    # Set material properties
    diffuse_color = Gf.Vec3f(*AnimationConfig.MATERIAL_DIFFUSE_COLOR)
    surface_shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(diffuse_color)
    # surface_shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(AnimationConfig.MATERIAL_METALLIC)
    # surface_shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(AnimationConfig.MATERIAL_ROUGHNESS)
    
    # Connect shader to material surface output
    material_surface_output = material.CreateSurfaceOutput()
    surface_output = surface_shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material_surface_output.ConnectToSource(surface_output)
    
    # Get the asset root prim (/ASSET)
    asset_prim: Usd.Prim = stage.GetPrimAtPath('/ASSET')
    if not asset_prim.IsValid():
        logger.warning("Asset prim not found at /ASSET, cannot apply material override")
        return stage
    
    # Bind material to asset with strongerThanDescendants
    binding_api: UsdShade.MaterialBindingAPI = UsdShade.MaterialBindingAPI.Apply(asset_prim)
    binding_api.Bind(material, UsdShade.Tokens.strongerThanDescendants)
    
    logger.info(f"Applied material override to /ASSET with strongerThanDescendants binding")
    
    return stage


def main(input_asset_path: str, output_folder: str) -> None:
    """
    Main function to process a USD asset and create animated test stages.
    
    Args:
        input_asset_path (str): Path to the input USD asset
        output_folder (str): Directory where output files will be created
    """
    
    # Validate configuration
    AnimationConfig.validate_config()
    
    # Log animation sequence
    phases = AnimationConfig.get_animation_phases()
    logger.info("Animation sequence:")
    for phase in phases:
        logger.info(f"  {phase['name']}: frames {phase['start']}-{phase['end']} ({phase['description']})")
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Validate input asset
    if not os.path.exists(input_asset_path):
        raise FileNotFoundError(f"Input asset not found: {input_asset_path}")
    
    logger.info(f"Processing asset: {input_asset_path}")
    logger.info(f"Output folder: {output_folder}")
    
    # Load asset and get properties
    try:
        loads_without_warnings_or_errors(input_asset_path)
        logger.info("Asset validation passed - no warnings or errors")
    except USDLoadingError as e:
        logger.warning(f"Asset loaded with warnings or errors, but continuing...\n{e}")
    
    asset_stage: Usd.Stage = Usd.Stage.Open(input_asset_path)
    asset_up_axis: str = UsdGeom.GetStageUpAxis(asset_stage)
    asset_bbox: Gf.BBox3d = _compute_stage_bounding_box(asset_stage, default_prim_only=True)
    
    # Define output file paths
    test_stage_path: str = os.path.join(output_folder, 'test_stage.usda')
    camera_layer_path: str = os.path.join(output_folder, 'camera_layer.usda')
    asset_animation_layer_path: str = os.path.join(output_folder, 'asset_animation.usda')
    lights_layer_path: str = os.path.join(output_folder, 'lights_animation.usda')
    
    logger.info(f"Creating test stage: {test_stage_path}")
    
    # Create and set up the test stage
    test_stage: Usd.Stage = setup_test_stage(input_asset_path, test_stage_path)

    # Create and frame camera
    if AnimationConfig.CAMERA_ENABLED:
        logger.info(f"Creating camera layer: {camera_layer_path}")
        camera_layer: Sdf.Layer = Sdf.Layer.CreateNew(camera_layer_path)
        Usd.Stage.Open(camera_layer).SetTimeCodesPerSecond(AnimationConfig.FRAME_RATE)
        test_stage.GetRootLayer().subLayerPaths.append(os.path.basename(camera_layer_path))
        test_stage.SetEditTarget(camera_layer)
        test_stage = create_and_frame_camera(stage=test_stage, asset_up_axis=asset_up_axis, asset_bbox=asset_bbox)
    else:
        logger.info("Camera creation disabled, skipping")

    # Create a single animation layer for asset animations
    logger.info(f"Creating asset animation layer: {asset_animation_layer_path}")
    asset_anim_layer: Sdf.Layer = Sdf.Layer.CreateNew(asset_animation_layer_path)
    Usd.Stage.Open(asset_anim_layer).SetTimeCodesPerSecond(AnimationConfig.FRAME_RATE)
    test_stage.GetRootLayer().subLayerPaths.append(os.path.basename(asset_animation_layer_path))
    test_stage.SetEditTarget(asset_anim_layer)
     
    # Apply asset animations using the shared layer with configured timing
    test_stage = spin_asset(test_stage, 
                           axis=AnimationConfig.ASSET_SPIN_Z_AXIS, 
                           start_time=AnimationConfig.ASSET_SPIN_Z_START, 
                           end_time=AnimationConfig.ASSET_SPIN_Z_END)
    test_stage = spin_asset(test_stage, 
                           axis=AnimationConfig.ASSET_SPIN_X_AXIS, 
                           start_time=AnimationConfig.ASSET_SPIN_X_START, 
                           end_time=AnimationConfig.ASSET_SPIN_X_END)
    test_stage = spin_asset(test_stage, 
                           axis=AnimationConfig.ASSET_SPIN_Y_AXIS, 
                           start_time=AnimationConfig.ASSET_SPIN_Y_START, 
                           end_time=AnimationConfig.ASSET_SPIN_Y_END)
    test_stage = move_asset(test_stage, asset_bbox)

    # Create separate layer for lights animation
    logger.info(f"Creating lights animation layer: {lights_layer_path}")
    lights_layer: Sdf.Layer = Sdf.Layer.CreateNew(lights_layer_path)
    Usd.Stage.Open(lights_layer).SetTimeCodesPerSecond(AnimationConfig.FRAME_RATE)
    test_stage.GetRootLayer().subLayerPaths.append(os.path.basename(lights_layer_path))
    test_stage.SetEditTarget(lights_layer)
    test_stage = spin_lights(test_stage, asset_up_axis)

    # Add origin visualization
    logger.info("Adding origin visualization")
    test_stage.SetEditTarget(test_stage.GetRootLayer())
    test_stage = create_origin_visualization(test_stage, asset_up_axis, asset_bbox)

    # Add size reference visualization
    logger.info("Adding size reference visualization")
    test_stage = create_size_reference_visualization(test_stage, asset_up_axis, asset_bbox)

    # Apply material override
    logger.info("Applying material override")
    test_stage = apply_material_override(test_stage)

    # Save the stage with asset animations
    test_stage.Save()
    
    logger.info("✅ Successfully created animated test stage and layers")
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create an animated USD test stage from an input asset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s asset.usd ./output/
  %(prog)s /path/to/asset.usda /path/to/output/folder/
  
This script will create several USD files in the output folder:
  - test_stage.usda (main stage with asset reference)
  - camera_layer.usda (framed camera)
  - asset_animation.usda (asset spinning and movement)
  - lights_animation.usda (spinning lights)
        """
    )
    
    parser.add_argument(
        "input_asset", 
        help="Path to the input USD asset file (.usd, .usda, .usdc)"
    )
    
    parser.add_argument(
        "output_folder",
        help="Directory where output files will be created (will be created if it doesn't exist)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    main(args.input_asset, args.output_folder)
    