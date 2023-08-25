#!/usr/bin/env python3
# Based on https://github.com/trishume/numderline/tree/master
# which was based on https://github.com/powerline/fontpatcher/blob/develop/scripts/powerline-fontpatcher

# STUFF I READ FOR THIS:
# https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html
# https://litherum.blogspot.com/2019/03/addition-font.html
# https://ansuz.sooke.bc.ca/entry/131
# https://tools.aftertheflood.com/sparks/
# https://blog.janestreet.com/commas-in-big-numbers-everywhere/

import argparse
import sys
import re
import subprocess
import os.path
import json
import shutil
import zipfile

from itertools import chain
from collections import defaultdict

try:
    import fontforge
    import psMat
    from fontTools.ttLib import TTFont
    from fontTools.feaLib.builder import addOpenTypeFeatures, Builder
except ImportError:
    sys.stderr.write('The required FontForge and fonttools modules could not be loaded.\n\n')
    sys.stderr.write('You need FontForge with Python bindings for this script to work.\n')
    sys.exit(1)


def get_argparser(ArgumentParser=argparse.ArgumentParser):
    parser = ArgumentParser(
    	description=('Font patcher for Hexagone. '
    	             'Requires FontForge with Python bindings. '
    	             'Stores the patched font as a new, renamed font file by default.')
    )
    parser.add_argument('fonts', help='font files to patch', metavar='font',
                        nargs='+', type=argparse.FileType('rb'))
    parser.add_argument('--no-rename',
                        help='don\'t add " for Powerline" to the font name',
                        default=True, action='store_false', dest='rename_font')
    return parser


FONT_NAME_RE = re.compile(r'^([^-]*)(?:(-.*))?$')
NUM_DIGIT_COPIES = 7

def name_for_decimal(decimal, hex_names):
    s = str(decimal)
    res = ""
    for c in s:
        res = res + " " + hex_names[int(c)]
    return res[1:]

oldf= """
languagesystem DFLT dflt;
languagesystem latn dflt;
languagesystem cyrl dflt;
languagesystem grek dflt;
languagesystem kana dflt;

@hex=[{hex_names}];

lookup P_REPLACE {{
    sub p by P P;
}} P_REPLACE;

lookup H_REPLACE {{
    sub h by H;
}} H_REPLACE;

lookup HEX_BIN {{
{hex_text}
}} HEX_BIN;

lookup HEX_DEC_ONE {{
    sub f f by f_f;
}} HEX_DEC_ONE;

lookup HEX_DEC_TWO {{
{hex_dec_two}
    # sub f_f by two five five comma;
}} HEX_DEC_TWO;

lookup HEX_DEC_TEST {{
    sub f a by three;
}} HEX_DEC_TEST;

feature liga {{
    #sub zero x by s_s;
    # sub r g b zero' x' by s_s;
{liga}
    # sub f' f' by f_f;
}} liga;

feature calt {{
    {calts}
    # sub f_f' lookup HEX_DEC_TWO;
    # sub z by Z;
    # sub h' lookup H_REPLACE;
}} calt;"""

"numbersign parenleft equal"

def write_feature_file(hex_names):
    sploot = hex_names.split()
    hex_text = []
    for num, name in enumerate(sploot):
        binned = bin(num)[2:]
        pad = (4 - len(binned)) * '0' + binned
        pad = pad.replace("0", "zero ")
        pad = pad.replace("1", "one ")
        pad = pad[:-1]

        hex_text.append(f"    sub {name} by {pad};")
    hex_text = "\n".join(hex_text)


    hex_decs = []
    hex_dec_ends = []
    ligas_notlast = []
    ligas_last = []
    mine = []
    mine_ends = []

    for outer, o_name in enumerate(sploot):
        for inner, i_name in enumerate(sploot):
            oi_name = f"{o_name}_{i_name}"
            mine.append(oi_name)
            mine_ends.append(oi_name + ".end")

            decimal = outer * 16 + inner
            dec_name = name_for_decimal(decimal, sploot)

            liga_notlast = f"   sub {o_name} {i_name} by {oi_name};"
            liga_last = f"   sub {o_name} {i_name} equal by {oi_name}.end;"
            
            #liga_rule = f"   sub parenright.mine' {o_name}' {i_name}' by {oi_name};"
            #liga_rule = f"   sub parenright.mine {o_name}' {i_name}' by {oi_name};"
            #liga_rule2 = f"   sub parenright {o_name}' {i_name}' by {oi_name};"
            hexdec_rule = f"   sub {oi_name}' by {dec_name} comma;"
            hexdec_end_rule = f"   sub {oi_name}.end' by {dec_name} parenright;"

            #calt_rule = f"   sub {oi_name}' lookup HEX_DEC;"
            #calt_end_rule = f"   sub {oi_name}.end' lookup HEX_DEC_END;"

            ligas_notlast.append(liga_notlast)
            ligas_last.append(liga_last)

            #ligas.append(liga_rule)
            #ligas.append(liga_rule2)
            hex_decs.append(hexdec_rule)
            hex_dec_ends.append(hexdec_end_rule)

            #calts.append(calt_rule)
            #calt_ends.append(calt_end_rule)
    
    ligas_notlast = "\n".join(ligas_notlast)
    ligas_last = "\n".join(ligas_last)

    hex_decs = "\n".join(hex_decs)
    hex_dec_ends = "\n".join(hex_dec_ends)

    mine = "\n".join(mine)
    mine_ends = "\n".join(mine_ends)


    feature = f"""
languagesystem DFLT dflt;
languagesystem latn dflt;
languagesystem cyrl dflt;
languagesystem grek dflt;
languagesystem kana dflt;

@hex=[{hex_names}];
@digit=[zero one two three four five six seven eight nine];
@mine=[{mine}];
@mineend=[{mine_ends}];

lookup HEX_DEC {{
{hex_decs}
}} HEX_DEC;

lookup HEX_DEC_END {{
{hex_dec_ends}
}} HEX_DEC_END;

lookup LIGA_LAST {{
{ligas_last}
}} LIGA_LAST;

lookup LIGA_NOTLAST {{
{ligas_notlast}
}} LIGA_NOTLAST;

feature liga {{
    # THIS WORKS
    sub numbersign @hex' lookup LIGA_NOTLAST @hex' @hex @hex @hex @hex equal;
    sub numbersign @mine @hex' lookup LIGA_NOTLAST @hex'  @hex @hex equal;
    sub numbersign @mine @mine @hex' lookup LIGA_LAST @hex' equal';
}} liga;

feature calt {{
    sub numbersign' @mine @mine @mine by parenleft;
    sub @mine' lookup HEX_DEC;
    sub @mineend' lookup HEX_DEC_END;
}} calt;
"""[1:]

    with open('mods.fea', 'w') as f:
        f.write(feature)

def patch_one_font(font, rename_font=True):
    font.encoding = 'ISO10646'

    # Rename font
    if rename_font:
        font.familyname += " for Hexagone5z"
        font.fullname += " for Hexagoneza122"
        fontname, style = FONT_NAME_RE.match(font.fontname).groups()
        font.fontname = fontname + 'ForHexagone'
        if style is not None:
            font.fontname += style
        font.appendSFNTName(
            'English (US)', 'Preferred Family', font.familyname)
        font.appendSFNTName(
            'English (US)', 'Compatible Full', font.fullname)


    hex_names = []
    for i in range(16):
        h = hex(i)[2:]
        hex_names.append(font[ord(h)].glyphname)
    hex_names = " ".join(hex_names)

    def hexify(s):
        d = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
        if s in d: return d[s]
        return s

    var = 0xE900
    for i in range(16):
        for j in range(16):
            fst = hexify(hex(i)[2:])
            snd = hexify(hex(j)[2:])

            h = fst + "_" + snd
            font.selection.select("h")
            font.copy()
            font.selection.select(var)
            font.paste()
            font[var].glyphname = h
            var += 1 

            h2 = fst + "_" + snd + ".end"
            font.selection.select("h")
            font.copy()
            font.selection.select(var)
            font.paste()
            font[var].glyphname = h2
            var += 1 

    font.selection.select("parenright")
    font.copy()
    font.selection.select(var)
    font.paste()
    font[var].glyphname = "parenright.mine"

    var +=1 
    font.selection.select("parenleft")
    font.copy()
    font.selection.select(var)
    font.paste()
    font[var].glyphname = "parenleft.mine"

    write_feature_file(hex_names)
    font.generate("out/tmp.ttf")
    ft_font = TTFont("out/tmp.ttf")
    addOpenTypeFeatures(ft_font, 'mods.fea', tables=['GSUB'])

    # Generate patched font
    extension = os.path.splitext(font.path)[1]
    if extension.lower() not in ['.ttf', '.otf']:
    	# Default to OpenType if input is not TrueType/OpenType
    	extension = '.otf'

    out_name = "{0}{1}".format(font.fullname, extension)
    ft_font.save(f"out/{out_name}")
    #font.generate('{0}{1}'.format(font.fullname, extension))


def patch_fonts(target_files, rename_font=True):
    for target_file in target_files:
    	font = fontforge.open(target_file.name)
    	try:
    		patch_one_font(font, rename_font)
    	finally:
    		font.close()
    return 0


def main(argv):
    args = get_argparser().parse_args(argv)
    return patch_fonts(args.fonts, args.rename_font)


raise SystemExit(main(sys.argv[1:]))
