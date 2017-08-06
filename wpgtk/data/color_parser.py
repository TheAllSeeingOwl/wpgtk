#!/usr/bin/env python3
import fileinput
import shutil
import sys
from subprocess import call
from os import walk
from colorsys import rgb_to_hls, hls_to_rgb
from random import randint
from . import config
import pywal


def get_color_list(image_name):
    image = pywal.image.get(config.WALL_DIR / image_name)
    color_dict = pywal.colors.get(image, config.WALL_DIR)
    return [v for v in color_dict['colors'].values()]


def write_colors(img, color_list):
    image = pywal.image.get(config.WALL_DIR / img)
    color_dict = pywal.colors.get(image, config.WALL_DIR)

    for i, key in enumerate(color_dict['colors'].keys()):
        color_dict['colors'][key] = color_list[i]
    color_dict['special']['background'] = color_list[0]
    color_dict['special']['foreground'] = color_list[15]

    cache_file = config.SCHEME_DIR / \
        str(image).replace('/', '_').replace('.', '_')
    cache_file = cache_file.with_suffix('.json')

    pywal.export.color(color_dict, "json", cache_file)
    pywal.export.color(color_dict,
                       "xresources",
                       config.XRES_DIR / (img + ".Xres"))


def change_colors(colors, which):
    opt = which
    if which in config.FILE_DIC:
        which = config.FILE_DIC[which]
    try:
        tmp_filename = str(which) + '.base'
        with open(tmp_filename, 'r') as tmp_file:
            tmp_data = tmp_file.read()

        for k, v in colors['wpgtk'].items():
            tmp_data = tmp_data.replace(k, v.strip('#'))
        for i, v in enumerate(colors['colors'].values()):
            replace_word = f'COLOR{i}' if i < 10 else f'COLORX{i}'
            tmp_data = tmp_data.replace(replace_word, v.strip('#'))
        for k, v in colors['icons'].items():
            tmp_data = tmp_data.replace(k, v.replace('#', ''))

        with open(str(which), 'w') as target_file:
            target_file.write(tmp_data)
        print(f"OK:: {str(opt).upper()} - CHANGED SUCCESSFULLY")
    except IOError as err:
        print(f"ERR::{str(opt).upper()} - \
              BASE FILE DOES NOT EXIST", file=sys.stderr)


def clean_icon_color(dirty_string):
    dirty_string = dirty_string.strip("\n")
    dirty_string = dirty_string.split("=")
    dirty_string = dirty_string.pop()
    return dirty_string


def get_darkness(hexv):
    rgb = list(int(hexv.strip('#')[i:i+2], 16) for i in (0, 2, 4))
    hls = rgb_to_hls(rgb[0], rgb[1], rgb[2])
    hls = list(hls)
    return hls[1]


def reduce_brightness(hex_string, reduce_lvl):
    rgb = list(int(hex_string.strip('#')[i:i+2], 16) for i in (0, 2, 4))
    hls = rgb_to_hls(rgb[0], rgb[1], rgb[2])
    hls = list(hls)
    if(hls[1] - reduce_lvl > 0):
        hls[1] = hls[1] - reduce_lvl
        rgb = hls_to_rgb(hls[0], hls[1], hls[2])
        rgb_int = []
        for elem in rgb:
            if(elem <= 0):
                elem = 5
            rgb_int.append(int(elem))
        rgb_int = tuple(rgb_int)
        hex_result = '%02x%02x%02x' % rgb_int
        return f"#{hex_result}"
    else:
        return reduce_brightness(hex_string, reduce_lvl - 5)


def add_brightness(hex_string, reduce_lvl):
    rgb = list(int(hex_string.strip('#')[i:i+2], 16) for i in (0, 2, 4))
    hls = rgb_to_hls(rgb[0], rgb[1], rgb[2])
    hls = list(hls)
    if(hls[1] + reduce_lvl < 250):
        hls[1] = hls[1] + reduce_lvl
        rgb = hls_to_rgb(hls[0], hls[1], hls[2])
        rgb_int = []
        for elem in rgb:
            if(elem > 255):
                elem = 254
            rgb_int.append(int(elem))
        rgb_int = tuple(rgb_int)
        hex_result = '%02x%02x%02x' % rgb_int
        return f"#{hex_result}"
    else:
        return add_brightness(hex_string, reduce_lvl - 5)
    rgb = hls_to_rgb(hls[0], hls[1], hls[2])
    rgb_int = []
    for elem in rgb:
        rgb_int.append(int(elem))
    rgb_int = tuple(rgb_int)
    hex_result = '%02x%02x%02x' % rgb_int
    return f"#{hex_result}"


def prepare_icon_colors(colors):
    try:
        glyph = reduce_brightness(colors['wpgtk']['COLORIN'], 15)
        file_current_glyph = open(config.FILE_DIC['icon-step1'], "r")
        current_back = ""
        current_front = ""
        current_glyph = ""
        for line in file_current_glyph:
            if("New" in line and "glyph" in line):
                current_glyph = clean_icon_color(line)
                break
        for line in file_current_glyph:
            if("New" in line and "front" in line):
                current_front = clean_icon_color(line)
                break
        for line in file_current_glyph:
            if("New" in line and "back" in line):
                current_back = clean_icon_color(line)
                break
        file_current_glyph.close()

        icon_dic = {"l=178984": "l=" + current_glyph,
                    "w=178984": "w=" + glyph,
                    "l=36d7b7": "l=" + current_front,
                    "w=36d7b7": "w=" + colors['wpgtk']['COLORACT'],
                    "l=1ba39c": "l=" + current_back,
                    "w=1ba39c": "w=" + colors['wpgtk']['COLORIN']}
        return icon_dic
    except IOError:
        print("ERR::ICONS - BASE FILES DO NOT EXIST", file=sys.stderr)
        return


def change_other_files(colors):
    other_path = config.HOME / ".themes/color_other"
    files = []
    for(dirpath, dirnames, filenames) in walk(other_path):
        files.extend(filenames)
    if files:
        try:
            for word in files:
                if ".base" in word:
                    original = word.split(".base", len(word)).pop(0)
                    change_colors(colors, other_path / original)
        except Exception as e:
            print('ERR:: ' + str(e), file=sys.stderr)
            print('ERR::OPTIONAL FILE -' + original, file=sys.stderr)
    else:
        print("INF::NO OPTIONAL FILES DETECTED")


def define_redux(hexvalue):
    base_brightness = get_darkness(hexvalue)
    if(hexvalue == "4A838F"):
        return [0, 50]
    elif base_brightness >= 190:
        return [60, 115]
    elif base_brightness >= 160:
        return [50, 105]
    elif base_brightness <= 10:
        return [-35, -15]
    elif base_brightness <= 60:
        return [-20, -5]
    elif base_brightness <= 70:
        return [0, 15]
    elif base_brightness <= 80:
        return [5, 20]
    elif base_brightness <= 125:
        return [20, 55]
    else:
        return [30, 75]


def prepare_colors(image_name):
    image = pywal.image.get(config.WALL_DIR / image_name)
    cdic = pywal.colors.get(image, config.WALL_DIR)

    wpcol = cdic['wpgtk'] = {}
    cl = [val for val in cdic['colors'].values()]

    if(config.wpgtk.getint('active') > 0):
        wpcol['BASECOLOR'] = cl[config.wpgtk.getint('active') - 1]
    else:
        print(f"random: {cl[randint(0,15)]}")
        wpcol['BASECOLOR'] = cl[randint(0, 15)]

    reduce_levels = define_redux(wpcol['BASECOLOR'])

    wpcol['COLORACT'] = reduce_brightness(wpcol['BASECOLOR'], reduce_levels[0])
    wpcol['COLORIN'] = reduce_brightness(wpcol['BASECOLOR'], reduce_levels[1])
    wpcol['COLORBASE'] = cl[0]
    wpcol['COLORBG'] = reduce_brightness(cl[0], 5)
    wpcol['COLORTOOL'] = add_brightness(cl[0], 10)
    wpcol['REPLAC'] = add_brightness(wpcol['COLORACT'], 70)

    cdic['icons'] = prepare_icon_colors(cdic)

    print("INF::FG: " + wpcol['COLORACT'])
    print("INF::BG: " + wpcol['COLORIN'])

    return cdic


def execute_gcolorchange(image_name):
    # Getting random color from an .Xres file--#
    # Defining how dark the windows have to be--#
    colors = prepare_colors(image_name)
    if config.wpgtk.getboolean('openbox') or not shutil.which('openbox'):
        change_colors(colors, 'openbox')
        call(["openbox", "--reconfigure"])

    if config.wpgtk.getboolean('tint2') or not shutil.which('tint2'):
        change_colors(colors, 'tint2')
        call(["killall", "-SIGUSR1", "tint2"])

    if config.wpgtk.getboolean('gtk'):
        change_colors(colors, 'gtk2')
        change_colors(colors, 'gtk3.0')
        change_colors(colors, 'gtk3.20')
        pywal.reload.gtk()

    change_other_files(colors)

    change_colors(colors, 'icon-step1')
    call(str(config.FILE_DIC['icon-step2']))
    print("OK::FINISHED")
