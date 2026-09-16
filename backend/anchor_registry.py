"""
Anchor Registry — Dynamic Object Cohesion for Multi-Product Composition

When an interior designer places multiple items in a room, they don't treat
each object in isolation. A rug anchors a seating group, a table anchors
decorative objects, and a sofa anchors cushions. If the rug moves, the whole
group moves with it.

This module implements that logic via a parent-child hierarchy:
  - Rug → Sofa → Cushion/Throw
  - Table → Vase/Lamp/Frame
  - Shelf → Bookend/Figurine

Usage:
    registry = AnchorRegistry()
    registry.register("rug_001", "floor_large", (100, 400, 600, 550))
    registry.register("sofa_002", "floor_large", (150, 300, 550, 540))
    # sofa auto-parents to rug because it overlaps
    registry.move("rug_001", dx=50, dy=0)  # sofa moves too
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ── Hierarchy Rules ───────────────────────────────────────────────────────
# Higher tier number = higher in the hierarchy (parent).
# A product can only be parented to a product with a HIGHER tier.
# Tier 0 items cannot be parents (they are always leaves).

PRODUCT_TIERS = {
    # Tier 3: Ground anchors — these are the roots of composition groups
    "rug": 3,
    "carpet": 3,
    "mat": 3,
    "runner": 3,
    
    # Tier 2: Large furniture — anchored by rugs, anchor small items
    "sofa": 2,
    "couch": 2,
    "sectional": 2,
    "armchair": 2,
    "table": 2,
    "desk": 2,
    "console": 2,
    "cabinet": 2,
    "shelf": 2,
    "bookshelf": 2,
    "sideboard": 2,
    "dresser": 2,
    "bed": 2,
    "bench": 2,
    "ottoman": 2,
    
    # Tier 1: Medium items — anchored by furniture
    "lamp": 1,
    "chair": 1,
    "stool": 1,
    "pouf": 1,
    "side table": 1,
    "nightstand": 1,
    "coffee table": 1,
    
    # Tier 0: Decorative — always leaf nodes, anchored by anything above
    "vase": 0,
    "frame": 0,
    "clock": 0,
    "mirror": 0,
    "candle": 0,
    "figurine": 0,
    "plant": 0,
    "cushion": 0,
    "throw": 0,
    "bookend": 0,
    "tray": 0,
    "sculpture": 0,
    "basket": 0,
}

# Default tier for unknown products
DEFAULT_TIER = 1

# Minimum bounding-box overlap (IoU) to establish parent-child relationship
MIN_OVERLAP_RATIO = 0.15


@dataclass
class AnchoredObject:
    """A placed object in the room with its spatial and hierarchy data."""
    object_id: str
    product_type: str           # From _classify_product() or product name
    tier: int                   # Hierarchy tier (higher = potential parent)
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) in room coordinates
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]
    
    @property
    def center(self) -> Tuple[int, int]:
        return (
            (self.bbox[0] + self.bbox[2]) // 2,
            (self.bbox[1] + self.bbox[3]) // 2,
        )
    
    @property
    def area(self) -> int:
        return self.width * self.height


def _get_tier(product_type: str, product_name: str = "") -> int:
    """
    Determine the hierarchy tier from the product type or name.
    Scans both the classified type and the product name for keywords.
    """
    searchable = f"{product_type} {product_name}".lower()
    
    best_tier = None
    for keyword, tier in PRODUCT_TIERS.items():
        if keyword in searchable:
            if best_tier is None or tier > best_tier:
                best_tier = tier
    
    return best_tier if best_tier is not None else DEFAULT_TIER


def _compute_overlap_ratio(bbox_a: Tuple[int, int, int, int],
                            bbox_b: Tuple[int, int, int, int]) -> float:
    """
    Compute the overlap ratio between two bounding boxes.
    Returns: area of intersection / area of smaller box.
    This measures how much the smaller object sits "on" the larger one.
    """
    x1 = max(bbox_a[0], bbox_b[0])
    y1 = max(bbox_a[1], bbox_b[1])
    x2 = min(bbox_a[2], bbox_b[2])
    y2 = min(bbox_a[3], bbox_b[3])
    
    if x2 <= x1 or y2 <= y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area_a = (bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1])
    area_b = (bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1])
    smaller_area = min(area_a, area_b)
    
    if smaller_area <= 0:
        return 0.0
    
    return intersection / smaller_area


class AnchorRegistry:
    """
    Manages parent-child relationships between placed objects in a room.
    
    When a new product is registered, the registry automatically:
      1. Determines its hierarchy tier (rug=3 > sofa=2 > vase=0)
      2. Finds the best parent among existing objects (highest-tier
         object with sufficient bounding-box overlap)
      3. Establishes the parent-child link
    
    When a parent object is moved, all its children move with it,
    maintaining their relative offsets.
    """
    
    def __init__(self):
        self._objects: Dict[str, AnchoredObject] = {}
    
    @property
    def objects(self) -> Dict[str, AnchoredObject]:
        return dict(self._objects)
    
    def clear(self):
        """Remove all registered objects."""
        self._objects.clear()
    
    def register(
        self,
        object_id: str,
        product_type: str,
        bbox: Tuple[int, int, int, int],
        product_name: str = "",
        metadata: Optional[Dict] = None,
    ) -> AnchoredObject:
        """
        Register a newly placed object in the room.
        
        Automatically finds the best parent from existing objects based on:
          - Bounding-box overlap (must exceed MIN_OVERLAP_RATIO)
          - Hierarchy tier (parent must be higher tier)
          - Largest overlap wins if multiple parents qualify
        
        Args:
            object_id: Unique ID for this placed object
            product_type: Product classification (e.g., "floor_large")
            bbox: (x1, y1, x2, y2) bounding box in room pixel coordinates
            product_name: Product name for tier detection
            metadata: Optional extra metadata to store
        
        Returns:
            The created AnchoredObject with parent assigned (if found)
        """
        tier = _get_tier(product_type, product_name)
        
        obj = AnchoredObject(
            object_id=object_id,
            product_type=product_type,
            tier=tier,
            bbox=bbox,
            metadata=metadata or {},
        )
        
        # Find the best parent: highest-tier object with sufficient overlap
        best_parent = None
        best_overlap = MIN_OVERLAP_RATIO
        
        for existing_id, existing_obj in self._objects.items():
            # Parent must be a higher tier
            if existing_obj.tier <= tier:
                continue
            
            overlap = _compute_overlap_ratio(bbox, existing_obj.bbox)
            if overlap > best_overlap:
                best_overlap = overlap
                best_parent = existing_obj
        
        if best_parent:
            obj.parent_id = best_parent.object_id
            best_parent.children_ids.append(object_id)
            print(f"[AnchorRegistry] '{object_id}' (tier={tier}) → "
                  f"parented to '{best_parent.object_id}' (tier={best_parent.tier}, "
                  f"overlap={best_overlap:.1%})")
        else:
            print(f"[AnchorRegistry] '{object_id}' (tier={tier}) → root object (no parent)")
        
        self._objects[object_id] = obj
        return obj
    
    def move(self, object_id: str, dx: int, dy: int) -> List[str]:
        """
        Move an object and all its descendants by (dx, dy).
        
        When a rug moves, the sofa on it moves, and the vase on the sofa
        moves too — maintaining all relative positions.
        
        Args:
            object_id: ID of the object to move
            dx, dy: Pixel offset to apply
        
        Returns:
            List of all object IDs that were moved (for logging)
        """
        if object_id not in self._objects:
            return []
        
        moved = []
        self._move_recursive(object_id, dx, dy, moved)
        return moved
    
    def _move_recursive(self, object_id: str, dx: int, dy: int, moved: List[str]):
        """Recursively move an object and all its children."""
        obj = self._objects.get(object_id)
        if not obj:
            return
        
        # Move this object
        x1, y1, x2, y2 = obj.bbox
        obj.bbox = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
        moved.append(object_id)
        
        # Recursively move all children
        for child_id in obj.children_ids:
            self._move_recursive(child_id, dx, dy, moved)
    
    def unregister(self, object_id: str) -> bool:
        """
        Remove an object from the registry.
        
        If the object has children, they become root objects (unparented).
        If the object has a parent, it is removed from the parent's children.
        
        Returns:
            True if the object was found and removed.
        """
        obj = self._objects.get(object_id)
        if not obj:
            return False
        
        # Remove from parent's children list
        if obj.parent_id and obj.parent_id in self._objects:
            parent = self._objects[obj.parent_id]
            parent.children_ids = [c for c in parent.children_ids if c != object_id]
        
        # Orphan all children (they become root objects)
        for child_id in obj.children_ids:
            if child_id in self._objects:
                self._objects[child_id].parent_id = None
                print(f"[AnchorRegistry] '{child_id}' orphaned (parent '{object_id}' removed)")
        
        del self._objects[object_id]
        return True
    
    def get_group(self, object_id: str) -> List[str]:
        """
        Get all objects in the same group as the given object.
        Walks up to the root parent, then collects all descendants.
        """
        if object_id not in self._objects:
            return []
        
        # Walk up to root
        root_id = object_id
        while self._objects[root_id].parent_id:
            root_id = self._objects[root_id].parent_id
            if root_id not in self._objects:
                break
        
        # Collect all descendants from root
        group = []
        self._collect_descendants(root_id, group)
        return group
    
    def _collect_descendants(self, object_id: str, result: List[str]):
        """Recursively collect an object and all its descendants."""
        obj = self._objects.get(object_id)
        if not obj:
            return
        result.append(object_id)
        for child_id in obj.children_ids:
            self._collect_descendants(child_id, result)
    
    def get_placement_constraints(self, product_type: str, product_name: str = "") -> Optional[Tuple[int, int, int, int]]:
        """
        Suggest a constrained placement region for a new product based on
        existing anchors.
        
        Example: If a rug is registered at (100, 400, 600, 550), and we're
        placing a "vase" (tier 0), suggest placing it WITHIN the rug's bbox
        or on top of a table within that rug group.
        
        Returns:
            Suggested (x1, y1, x2, y2) constraint region, or None if no
            suitable anchor exists.
        """
        tier = _get_tier(product_type, product_name)
        
        # Find the best anchor: highest-tier object that could parent this product
        best_anchor = None
        best_tier = -1
        
        for obj in self._objects.values():
            if obj.tier > tier and obj.tier > best_tier:
                best_anchor = obj
                best_tier = obj.tier
        
        if best_anchor:
            # Constrain placement to within the anchor's bounding box
            # with some padding for visual offset
            pad_x = best_anchor.width // 8
            pad_y = best_anchor.height // 8
            return (
                best_anchor.bbox[0] + pad_x,
                best_anchor.bbox[1] + pad_y,
                best_anchor.bbox[2] - pad_x,
                best_anchor.bbox[3] - pad_y,
            )
        
        return None
    
    def get_hierarchy_summary(self) -> str:
        """Return a human-readable summary of the object hierarchy."""
        if not self._objects:
            return "[AnchorRegistry] Empty — no objects registered"
        
        lines = ["[AnchorRegistry] Hierarchy:"]
        
        # Find root objects (no parent)
        roots = [obj for obj in self._objects.values() if not obj.parent_id]
        
        for root in sorted(roots, key=lambda o: o.tier, reverse=True):
            self._format_tree(root, lines, indent=1)
        
        return "\n".join(lines)
    
    def _format_tree(self, obj: AnchoredObject, lines: List[str], indent: int):
        """Recursively format the hierarchy tree."""
        prefix = "  " * indent + ("└─ " if indent > 1 else "├─ ")
        lines.append(f"{prefix}{obj.object_id} [tier={obj.tier}, "
                     f"bbox=({obj.bbox[0]},{obj.bbox[1]})-({obj.bbox[2]},{obj.bbox[3]})]")
        
        for child_id in obj.children_ids:
            child = self._objects.get(child_id)
            if child:
                self._format_tree(child, lines, indent + 1)
