#!/usr/bin/env python3
"""
Сервис управления фоновыми шаблонами для генерации контента
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import io
import random
import logging
from typing import Tuple, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BackgroundTemplate:
    """Описание шаблона фона"""
    template_id: str
    name: str
    background_color: Tuple[int, int, int]
    accent_color: Tuple[int, int, int]
    pattern_type: str  # 'solid', 'gradient', 'subtle_pattern'
    corner_radius: int = 20
    shadow_offset: int = 10
    border_width: int = 2

class BackgroundTemplates:
    """Класс для работы с фоновыми шаблонами"""

    # Профессиональные фоны для B2B
    PROFESSIONAL_BACKGROUNDS = {
        "professional_white": BackgroundTemplate(
            template_id="professional_white",
            name="Профессиональный белый",
            background_color=(255, 255, 255),
            accent_color=(240, 240, 240),
            pattern_type="solid",
            corner_radius=15,
            shadow_offset=8,
            border_width=1
        ),
        "professional_gray": BackgroundTemplate(
            template_id="professional_gray",
            name="Профессиональный серый",
            background_color=(245, 245, 245),
            accent_color=(230, 230, 230),
            pattern_type="solid",
            corner_radius=15,
            shadow_offset=8,
            border_width=1
        ),
        "professional_black": BackgroundTemplate(
            template_id="professional_black",
            name="Профессиональный черный",
            background_color=(35, 35, 35),
            accent_color=(60, 60, 60),
            pattern_type="solid",
            corner_radius=15,
            shadow_offset=8,
            border_width=2
        ),
    }

    # Маркетинговые фоны
    MARKETING_BACKGROUNDS = {
        "marketing_blue": BackgroundTemplate(
            template_id="marketing_blue",
            name="Маркетинговый синий",
            background_color=(240, 248, 255),
            accent_color=(200, 230, 255),
            pattern_type="gradient",
            corner_radius=20,
            shadow_offset=12,
            border_width=2
        ),
        "marketing_green": BackgroundTemplate(
            template_id="marketing_green",
            name="Маркетинговый зеленый",
            background_color=(240, 255, 240),
            accent_color=(200, 255, 200),
            pattern_type="gradient",
            corner_radius=20,
            shadow_offset=12,
            border_width=2
        ),
    }

    def __init__(self):
        """Инициализация сервиса фонов"""
        self.all_templates = {**self.PROFESSIONAL_BACKGROUNDS, **self.MARKETING_BACKGROUNDS}
        logger.info(f"Загружено {len(self.all_templates)} фоновых шаблонов")

    def get_template_by_id(self, template_id: str) -> BackgroundTemplate:
        """Получить шаблон по ID"""
        template = self.all_templates.get(template_id)
        if not template:
            logger.warning(f"Шаблон {template_id} не найден, используем стандартный")
            return self.PROFESSIONAL_BACKGROUNDS["professional_white"]
        return template

    def get_random_template(self, category: str = "professional") -> BackgroundTemplate:
        """Получить случайный шаблон из категории"""
        if category == "professional":
            templates = list(self.PROFESSIONAL_BACKGROUNDS.values())
        elif category == "marketing":
            templates = list(self.MARKETING_BACKGROUNDS.values())
        else:
            templates = list(self.all_templates.values())

        return random.choice(templates)

    def create_gradient_background(self, template: BackgroundTemplate, size: Tuple[int, int]) -> Image.Image:
        """Создать градиентный фон"""
        width, height = size
        image = Image.new('RGB', size, template.background_color)
        draw = ImageDraw.Draw(image)

        # Создаем градиент
        if template.pattern_type == "gradient":
            for y in range(height):
                progress = y / height
                r = int(template.background_color[0] + (template.accent_color[0] - template.background_color[0]) * progress)
                g = int(template.background_color[1] + (template.accent_color[1] - template.background_color[1]) * progress)
                b = int(template.background_color[2] + (template.accent_color[2] - template.background_color[2]) * progress)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

        return image

    def create_solid_background(self, template: BackgroundTemplate, size: Tuple[int, int]) -> Image.Image:
        """Создать однотонный фон с узором"""
        width, height = size
        image = Image.new('RGB', size, template.background_color)
        draw = ImageDraw.Draw(image)

        # Добавляем узор для однотонных фонов
        if template.pattern_type == "solid":
            # Создаем сетку или точки
            spacing = 50
            for x in range(0, width, spacing):
                draw.line([(x, 0), (x, height)], fill=template.accent_color, width=1)
            for y in range(0, height, spacing):
                draw.line([(0, y), (width, y)], fill=template.accent_color, width=1)

        return image

    def apply_background(self, product_image: Image.Image, template_id: str) -> Image.Image:
        """
        Применить фон к изображению товара

        Args:
            product_image: Изображение товара (PIL Image)
            template_id: ID шаблона фона

        Returns:
            Image: Изображение с примененным фоном
        """
        try:
            template = self.get_template_by_id(template_id)

            # Определяем размеры финального изображения (16:9 формат)
            target_width = 1920
            target_height = 1080

            # Создаем фон
            if template.pattern_type == "gradient":
                background = self.create_gradient_background(template, (target_width, target_height))
            else:
                background = self.create_solid_background(template, (target_width, target_height))

            # Оптимизируем изображение товара
            product_image = self._optimize_product_image(product_image)

            # Размещаем товар на фоне (более 50% площади)
            product_placement = self._calculate_product_placement(
                product_image.size, (target_width, target_height)
            )

            # Применяем тень и рамку к товару
            product_with_effects = self._apply_product_effects(product_image, template)

            # Размещаем товар на фоне
            x = (target_width - product_placement[0]) // 2
            y = (target_height - product_placement[1]) // 2

            # Изменяем размер товара с сохранением пропорций
            product_resized = product_with_effects.resize(product_placement, Image.Resampling.LANCZOS)

            # Создаем маску для размещения товара с закругленными углами
            mask = Image.new('L', product_placement, 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle(
                [(0, 0), product_placement],
                radius=template.corner_radius,
                fill=255
            )

            # Размещаем товар на фоне
            background.paste(product_resized, (x, y), mask)

            # Добавляем финальные эффекты (border, watermark и т.д.)
            final_image = self._apply_final_effects(background, template)

            logger.info(f"Фон {template.name} успешно применен к изображению")
            return final_image

        except Exception as e:
            logger.error(f"Ошибка при применении фона: {e}")
            raise

    def _optimize_product_image(self, image: Image.Image) -> Image.Image:
        """Оптимизировать изображение товара для лучшего вида"""
        try:
            # Улучшаем контрастность и яркость
            from PIL import ImageEnhance

            # Увеличиваем контрастность
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)

            # Немного увеличиваем яркость
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)

            # Улучшаем резкость
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)

            return image

        except Exception as e:
            logger.warning(f"Не удалось оптимизировать изображение: {e}")
            return image

    def _calculate_product_placement(self, product_size: Tuple[int, int],
                                     canvas_size: Tuple[int, int]) -> Tuple[int, int]:
        """
        Рассчитать размер размещения товара (более 50% площади)

        Args:
            product_size: Размер изображения товара
            canvas_size: Размер канвы

        Returns:
            Tuple[int, int]: Оптимальный размер товара
        """
        product_width, product_height = product_size
        canvas_width, canvas_height = canvas_size

        # Рассчитываем площадь
        product_area = product_width * product_height
        canvas_area = canvas_width * canvas_height

        # Требуем минимально 50% площади
        min_area = canvas_area * 0.5

        # Если товар уже занимает достаточно места, уменьшаем до 60%
        if product_area >= min_area:
            scale = 0.6
        else:
            # Иначе увеличиваем до 50% площади
            scale = (min_area / product_area) ** 0.5
            scale = min(scale, 0.7)  # Не более 70% от канвы

        new_width = int(product_width * scale)
        new_height = int(product_height * scale)

        # Проверяем, что товар не выходит за рамки
        if new_width > canvas_width * 0.8:
            new_width = int(canvas_width * 0.8)
            new_height = int(new_height * (new_width / (product_width * scale)))

        if new_height > canvas_height * 0.8:
            new_height = int(canvas_height * 0.8)
            new_width = int(new_width * (new_height / (product_height * scale)))

        return (new_width, new_height)

    def _apply_product_effects(self, image: Image.Image,
                               template: BackgroundTemplate) -> Image.Image:
        """Применить эффекты к изображению товара"""
        try:
            # Создаем тень
            shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)

            # Рисуем тень
            for offset in range(template.shadow_offset, 0, -2):
                alpha = int(50 * (1 - offset / template.shadow_offset))
                shadow_draw.rounded_rectangle(
                    [(offset, offset),
                     (image.size[0] + offset - template.border_width,
                      image.size[1] + offset - template.border_width)],
                    radius=template.corner_radius,
                    fill=(0, 0, 0, alpha)
                )

            # Накладываем тень на изображение
            image_with_shadow = Image.new('RGBA', image.size, (255, 255, 255, 0))
            image_with_shadow.paste(shadow, (0, 0), shadow)
            image_with_shadow.paste(image, (0, 0), image)

            # Добавляем рамку
            final_image = Image.new('RGBA', image.size, (0, 0, 0, 0))
            border_color = template.accent_color if template.accent_color != template.background_color else (200, 200, 200)

            draw = ImageDraw.Draw(final_image)
            draw.rounded_rectangle(
                [(0, 0), (image.size[0] - 1, image.size[1] - 1)],
                radius=template.corner_radius,
                outline=border_color,
                width=template.border_width
            )

            final_image.paste(image_with_shadow, (0, 0), image_with_shadow)

            return final_image

        except Exception as e:
            logger.warning(f"Не удалось применить эффекты: {e}")
            return image

    def _apply_final_effects(self, image: Image.Image,
                             template: BackgroundTemplate) -> Image.Image:
        """Применить финальные эффекты к полному изображению"""
        try:
            # Добавляем watermark или брендинг
            if template.template_id.startswith("marketing"):
                draw = ImageDraw.Draw(image)

                # Добавляем текст watermark
                try:
                    # Пытаемся использовать системный шрифт
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()

                watermark_text = "MarketBot Pro"
                text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]

                # Размещаем watermark в правом нижнем углу
                x = image.size[0] - text_width - 20
                y = image.size[1] - 40

                # Полупрозрачный текст
                watermark = Image.new('RGBA', image.size, (255, 255, 255, 0))
                watermark_draw = ImageDraw.Draw(watermark)
                watermark_draw.text((x, y), watermark_text, fill=(150, 150, 150, 128), font=font)

                image = Image.alpha_composite(image, watermark)

            # Применяем легкий blur для более профессионального вида
            image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

            return image

        except Exception as e:
            logger.warning(f"Не удалось применить финальные эффекты: {e}")
            return image

    def get_available_templates(self) -> Dict[str, str]:
        """Получить список доступных шаблонов"""
        return {template_id: template.name for template_id, template in self.all_templates.items()}

    def preview_template(self, template_id: str, size: Tuple[int, int] = (300, 169)) -> Image.Image:
        """Создать превью шаблона"""
        template = self.get_template_by_id(template_id)

        if template.pattern_type == "gradient":
            return self.create_gradient_background(template, size)
        else:
            return self.create_solid_background(template, size)

# Глобальный экземпляр сервиса
_background_templates = None

def get_background_templates() -> BackgroundTemplates:
    """Получить экземпляр сервиса фоновых шаблонов"""
    global _background_templates
    if _background_templates is None:
        _background_templates = BackgroundTemplates()
    return _background_templates