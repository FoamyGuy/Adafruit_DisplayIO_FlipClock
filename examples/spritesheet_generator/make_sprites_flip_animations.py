# SPDX-FileCopyrightText: Copyright (c) 2022 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Command line script to generate flip clock spritesheet Bitmap image files.


"""

import typer
import math
from typing import Tuple, List
from PIL import Image, ImageDraw, ImageFont
import numpy

DEFAULT_FONT = "LeagueSpartan-Regular.ttf"
DEFAULT_FONT_SIZE = 44
TILE_WIDTH, TILE_HEIGHT = (48, 100)
TILE_COLOR = (90, 90, 90)
FONT_COLOR = (255, 255, 255)
PADDING_SIZE = 8
TRANSPARENCY_COLOR = (0, 255, 0)
BACKGROUND_COLOR = TRANSPARENCY_COLOR


def find_coeffs(pa: Tuple, pb: Tuple) -> numpy.ndarray:
    """
    Find the set of coefficients that can be used to apply a perspective transform
    from the shape of one given plane to the shape of another given plane.

    :param tuple pa: the 4 points that make up the first plane
    :param tuple pb: the 4 points that make up the second plane

    """
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])

    A = numpy.matrix(matrix, dtype=float)
    B = numpy.array(pb).reshape(8)

    res = numpy.dot(numpy.linalg.inv(A.T * A) * A.T, B)
    return numpy.array(res).reshape(8)


def find_top_half_coeffs_inputs_for_angle(img: Image.Image, angle: int) -> Tuple[List]:
    """
    Find the coefficient inputs for the top half of the image for a given angle.

    :param PIL.Image img: The image object representing the top half of the digit
    :param int angle: The angle in degrees (0-90) to generate the coefficients for

    :returns Tuple of Lists of input points that can be passed to the
     find_coefficient() function.
    """
    x_val = (angle * PADDING_SIZE) / 90
    y_val = min((angle * (img.height)) / 90, img.height - 1)

    first_list = [
        (-(x_val + 1), y_val),
        (img.width + x_val, y_val),
        (img.width, img.height),
        (0, img.height),
    ]
    second_list = [(0, 0), (img.width, 0), (img.width, img.height), (0, img.height)]
    return first_list, second_list


def find_bottom_half_coeffs_inputs_for_angle(img: Image.Image, angle: int) -> Tuple[List]:
    """
    Find the coefficient inputs for the bottom half of the image for a given angle.

    :param PIL.Image img: The image object representing the top half of the digit
    :param int angle: The angle in degrees (0-90) to generate the coefficients for.
    """
    x_val = ((90 - angle) * PADDING_SIZE) / 90
    y_val = min((angle * (img.height)) / 90, img.height - 1)
    # print(f"(x: {x_val}, y: {y_val})")
    first_list = [
        (0, 0),
        (img.width, 0),
        (img.width + x_val, y_val),
        (-(x_val + 1), y_val),
    ]
    second_list = [(0, 0), (img.width, 0), (img.width, img.height), (0, img.height)]
    return first_list, second_list


def get_top_half(img: Image.Image) -> Image.Image:
    """
    Return an Image object representing the top half of the input image

    :param Image img: input image

    :returns Image: PIL Image object containing the top half of the input image
    """
    top_half = img.crop((0, 0, img.width, img.height // 2))
    return top_half


def get_bottom_half(img: Image.Image) -> Image.Image:
    """
       Return an Image object representing the bottom half of the input image

       :param Image img: input image

       :returns Image: PIL Image object containing the bottom half of the input image
       """
    bottom_half = img.crop((0, img.height // 2, img.width, img.height))
    return bottom_half


def make_sprite(character: str, font_size: int = 44, font: str = DEFAULT_FONT) -> Image.Image:
    """
    Make a PIL Image object representing a single static digit (or character).
    These get packed into the static sprite sheet, and are used as the basis
    for the angled animation sprites.

    :param str character: A single digit or character to put on this static sprite
    :param int font_size: The size to render the font on the the sprite
    :param str font: The filename of the font to render the character in.
      Filetype must be otf, ttf, or other font formats supported by PIL.

    :returns Image: The PIL Image object containing a single static character sprite.
    """
    border_rect_size = (TILE_WIDTH - PADDING_SIZE, TILE_HEIGHT - PADDING_SIZE)
    # inner_image_size = (border_rect_size[0] + 1, border_rect_size[1] + 1)
    inner_image_size = (TILE_WIDTH, TILE_HEIGHT)
    border_shape = ((PADDING_SIZE, PADDING_SIZE), border_rect_size)

    fnt = ImageFont.truetype(font, font_size)
    img = Image.new("RGBA", (TILE_WIDTH, TILE_HEIGHT), color=BACKGROUND_COLOR)

    # d = ImageDraw.Draw(img)

    inner_img = Image.new("RGBA", inner_image_size, color=BACKGROUND_COLOR)

    inner_draw = ImageDraw.Draw(inner_img)
    # inner_draw.rectangle((0, 0, inner_image_size[0], inner_image_size[1]), fill=(100, 100, 200))

    inner_draw.rectangle(border_shape, outline=TILE_COLOR, fill=TILE_COLOR)

    w, h = inner_draw.textsize(character, font=fnt)
    inner_draw.text(
        (((inner_image_size[0] - w) // 2) - 1, ((inner_image_size[1] - h) // 2) - 1),
        character,
        fill=FONT_COLOR,
        font=fnt,
    )

    img.paste(inner_img, (PADDING_SIZE // 2, PADDING_SIZE // 2))

    # inner_img.save("test_inner.png")

    return inner_img


def make_angles_sprite_set(img: Image.Image, count: int = 10, bottom_skew: bool = False) -> List[Image.Image]:
    """
    Generate angled sprites from a static sprite image.

    :param Image img: input static image
    :param int count: number of animation frames to generate (default 10)
    :param bool bottom_skew: Whether to render the bottom angle or top angled sprites

    :returns List[Image]: A List of Image objects containing the angled sprites.
    """
    angled_sprites = []
    # test_sheet = Image.new('RGBA', (img.width * 5, img.height * 2), color=(0, 255, 0))
    # test_sheet.save("before_anything.png")

    angle_count_by = (90 // count) + 1
    for _, _angle in enumerate(range(0, 91, angle_count_by)):
        # print(f"angle: {_angle}")
        if bottom_skew:
            coeffs = find_coeffs(
                *find_bottom_half_coeffs_inputs_for_angle(img, _angle + 1)
            )
        else:  # top skew:
            coeffs = find_coeffs(
                *find_top_half_coeffs_inputs_for_angle(img, _angle + 1)
            )

        this_angle_img = img.transform(
            (img.width, img.height), Image.PERSPECTIVE, coeffs, Image.BICUBIC
        )

        # this_angle_img.save(f"test_out/top_half_inner_{_angle + 1}.png")

        # coords = (((_ % 5) * img.width), ((_ // 5) * img.height))
        # print(coords)

        angled_sprites.append(this_angle_img)

    return angled_sprites


def make_static_sheet(font_size: int = 44, font: str = DEFAULT_FONT) -> None:
    """
    Generate the spritesheet of static digit images. Outputs static sprite sheet
    file as "static_sheet.bmp"

    :param int font_size: the font size to render the text on the sprites at
    :param str font: the filename of the font to render the text in.
     Must be otf, ttf, or other format supported by PIL.

    """
    full_sheet_img = Image.new(
        "RGBA", (TILE_WIDTH * 3, TILE_HEIGHT * 4), color=BACKGROUND_COLOR
    )

    for i in range(10):
        img = make_sprite(f"{i}", font_size=font_size, font=font)
        # img.save(f'char_sprites/pil_text_{i}.png')
        coords = (((i % 3) * TILE_WIDTH), ((i // 3) * TILE_HEIGHT))
        # print(coords)
        full_sheet_img.paste(img, coords)

    img = make_sprite(":", font_size=font_size)
    coords = (((10 % 3) * TILE_WIDTH), ((10 // 3) * TILE_HEIGHT))
    full_sheet_img.paste(img, coords)

    full_sheet_img = full_sheet_img.convert(mode="P", palette=Image.WEB)
    full_sheet_img.save("static_sheet.bmp")


def pack_images_to_sheet(images: List[Image.Image], width: int) -> Image.Image:
    """
    Pack a list of PIL Image objects into a sprite sheet within
    another PIL Image object.

    :param List[Image] images: A list of Image objects to pack into the sheet
    :param int width: The number of sprites in each row

    :returns Image: PIL Image object containing the packed sprite sheet
    """
    row_count = math.ceil(len(images) / width)

    _img_width = images[0].width
    _img_height = images[0].height
    print(f"len: {len(images)} width:{width} img_w:{_img_width} img_h:{_img_height}")
    _sheet_img = Image.new(
        "RGBA", (_img_width * width, _img_height * row_count), color=TRANSPARENCY_COLOR
    )
    # _sheet_img.save("before_things.bmp")
    for i, image in enumerate(images):
        coords = (((i % width) * TILE_WIDTH), ((i // width) * image.height))
        print(coords)
        _sheet_img.paste(image, coords, image)
        # image.save(f"test_out/img_{i}.png")

    return _sheet_img


def make_animations_sheets(font_size: int = 44, font: str = DEFAULT_FONT) -> None:
    """
    Generate and save the top and bottom animation sprite sheets for the digits 0-9.
    Outputs the two spritesheets as "bottom_animation_sheet.bmp" and "top_animation_sheet.bmp"

    :param int font_size: the font size to render the text on the sprites at
    :param str font: the filename of the font to render the text in.
     Must be otf, ttf, or other format supported by PIL.
    """
    bottom_sprites = []
    top_sprites = []

    for i in range(10):
        img = make_sprite(f"{i}", font_size=font_size, font=font)
        top_half = get_top_half(img)
        bottom_half = get_bottom_half(img)

        bottom_angled_sprites = make_angles_sprite_set(
            bottom_half, 10, bottom_skew=True
        )
        top_angled_sprites = make_angles_sprite_set(top_half, 10, bottom_skew=False)

        bottom_sprites.extend(bottom_angled_sprites)
        top_sprites.extend(top_angled_sprites)

    bottom_sheet = pack_images_to_sheet(images=bottom_sprites, width=10)
    # bottom_sheet.save("test_bottom_sheet.png")

    bottom_sheet = bottom_sheet.convert(mode="P", palette=Image.WEB)
    bottom_sheet.save("bottom_animation_sheet.bmp")

    top_sheet = pack_images_to_sheet(images=top_sprites, width=10)
    top_sheet = top_sheet.convert(mode="P", palette=Image.WEB)
    top_sheet.save("top_animation_sheet.bmp")


def main(width: int = TILE_WIDTH, height: int = TILE_HEIGHT, padding: int = PADDING_SIZE,
         text_color: Tuple[int, int, int] = FONT_COLOR,
         background_color: Tuple[int, int, int] = TILE_COLOR,
         transparent_color: Tuple[int, int, int] = TRANSPARENCY_COLOR,
         font: str = DEFAULT_FONT, font_size: int = DEFAULT_FONT_SIZE,
         animation_frames: int = 10) -> None:
    make_static_sheet(font_size=font_size, font=font)
    make_animations_sheets(font_size=font_size, font=font)


if __name__ == "__main__":
    typer.run(main)

# if __name__ == '__main__':
#     make_static_sheet(font_size=44)
#     make_animations_sheets(font_size=44)
