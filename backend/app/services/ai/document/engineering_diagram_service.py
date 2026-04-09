"""Engineering Diagram Analysis Service — Gemma 4 Vision for survey/cadastral maps.

Analyzes engineering diagrams (測量圖, 地籍圖, 工程圖) to extract:
- Coordinates and boundaries
- Scale and orientation
- Parcel numbers / survey marks
- Area measurements
- Key annotations and labels

Version: 1.0.0
Created: 2026-04-05
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class EngineeringDiagramService:
    """Analyze engineering diagrams using Gemma 4 Vision."""

    _TYPE_PROMPTS = {
        "survey": (
            "分析此測量圖，提取以下資訊以 JSON 回覆：\n"
            '{"diagram_type": "測量圖", "coordinates": [{"point": "A", "x": 0, "y": 0}], '
            '"boundaries": [{"from": "A", "to": "B", "distance": "m"}], '
            '"survey_marks": ["mark1"], "scale": "1:1000", '
            '"orientation": "北", "area": "面積(㎡)", '
            '"annotations": ["標註1"], "summary": "圖面摘要"}'
        ),
        "cadastral": (
            "分析此地籍圖，提取以下資訊以 JSON 回覆：\n"
            '{"diagram_type": "地籍圖", "parcels": [{"number": "地號", "area": "㎡", '
            '"land_use": "用途"}], "section": "段", "district": "區", '
            '"boundaries": [], "roads": ["道路名"], '
            '"annotations": [], "summary": "圖面摘要"}'
        ),
        "engineering": (
            "分析此工程圖，提取以下資訊以 JSON 回覆：\n"
            '{"diagram_type": "工程圖", "structures": [{"name": "結構名", '
            '"dimensions": "尺寸"}], "materials": ["材料"], '
            '"scale": "比例", "annotations": [], "summary": "圖面摘要"}'
        ),
        "blueprint": (
            "分析此藍圖/平面圖，提取以下資訊以 JSON 回覆：\n"
            '{"diagram_type": "藍圖", "rooms": [{"name": "空間", "area": "㎡"}], '
            '"dimensions": [], "annotations": [], "summary": "圖面摘要"}'
        ),
    }

    async def analyze_diagram(
        self,
        image_bytes: bytes,
        diagram_type: str = "survey",
        context: str = "",
    ) -> Dict[str, Any]:
        """Analyze an engineering diagram image.

        Args:
            image_bytes: Raw image bytes (PNG/JPG/TIFF)
            diagram_type: survey(測量圖), cadastral(地籍圖),
                          engineering(工程圖), blueprint(藍圖)
            context: Optional context (e.g., project name, location)

        Returns:
            Structured analysis with coordinates, areas, annotations.
        """
        from app.core.ai_connector import get_ai_connector
        from app.services.ai.agent_utils import parse_json_safe

        ai = get_ai_connector()

        prompt = self._TYPE_PROMPTS.get(diagram_type, self._TYPE_PROMPTS["survey"])
        if context:
            prompt = f"背景: {context}\n\n{prompt}"
        prompt += "\n\n如果圖片模糊或無法辨識，在 summary 中說明。"

        try:
            result = await ai.vision_completion(
                prompt=prompt,
                image_bytes=image_bytes,
                temperature=0.2,
                max_tokens=1024,
                task_type="vision",
            )
            parsed = parse_json_safe(result)
            if parsed:
                parsed["_raw_response"] = result[:200]
                return parsed
            return {
                "diagram_type": diagram_type,
                "summary": result[:500],
                "_parse_failed": True,
            }
        except Exception as e:
            logger.error("Diagram analysis failed: %s", e)
            return {"error": str(e), "diagram_type": diagram_type}

    async def compare_diagrams(
        self,
        image_bytes_a: bytes,
        image_bytes_b: bytes,
        comparison_type: str = "change",
    ) -> Dict[str, Any]:
        """Compare two diagram versions (e.g., before/after survey)."""
        result_a = await self.analyze_diagram(image_bytes_a, "survey")
        result_b = await self.analyze_diagram(image_bytes_b, "survey")

        return {
            "diagram_a": result_a,
            "diagram_b": result_b,
            "comparison_type": comparison_type,
        }

    async def extract_coordinates_table(
        self,
        image_bytes: bytes,
    ) -> Dict[str, Any]:
        """Extract coordinate table from survey diagram."""
        from app.core.ai_connector import get_ai_connector
        from app.services.ai.agent_utils import parse_json_safe

        ai = get_ai_connector()
        prompt = (
            "此圖包含座標表或控制點資料。\n"
            "提取所有座標點以 JSON 回覆：\n"
            '{"coordinate_system": "TWD97/TWD67/WGS84", '
            '"points": [{"name": "點名", "x": 東距, "y": 北距, "z": 高程}], '
            '"datum": "基準面", "projection": "投影方式"}'
        )
        try:
            result = await ai.vision_completion(
                prompt=prompt,
                image_bytes=image_bytes,
                temperature=0.2,
                max_tokens=1024,
                task_type="vision",
            )
            parsed = parse_json_safe(result)
            if parsed:
                parsed["_raw_response"] = result[:200]
                return parsed
            return {"summary": result[:500], "_parse_failed": True}
        except Exception as e:
            logger.error("Coordinate extraction failed: %s", e)
            return {"error": str(e)}
