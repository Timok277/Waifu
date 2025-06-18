# -*- coding: utf-8 -*-

class Platform:
    """Представляет платформу, по которой может ходить персонаж (окно или край монитора)."""
    def __init__(self, left, top, right, bottom, platform_type='floor', is_target=False):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.platform_type = platform_type
        self.is_target = is_target

    @property
    def width(self):
        return self.right - self.left
        
    def __eq__(self, other):
        if not isinstance(other, Platform):
            return NotImplemented
        return (self.left == other.left and
                self.top == other.top and
                self.right == other.right and
                self.bottom == other.bottom and
                self.platform_type == other.platform_type) 