#!/usr/bin/env python

import sys
import os
import argparse
import json
import yaml
import fontforge


error = sys.stderr.write


# returns dict representing duplicate values of seq
# in seq = [1,1,2,3,3,3,3,4,5], out dict {1: 2, 3: 4}
def get_dups(seq):
    count = {}
    for s in seq:
        count[s] = count.get(s, 0) + 1
    dups = dict((k, v) for k, v in count.iteritems() if v > 1)
    return dups


def get_font(i, config_path, fonts_dir):
    try:
        config = yaml.load(open(config_path, 'r'))
    except IOError as (errno, strerror):
        error('Cannot open %s: %s\n' % (config_path, strerror))
        sys.exit(1)
    except yaml.YAMLError, e:
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            error('YAML parser error in file %s at line %d, col %d\n' %
                (config_path, mark.line + 1, mark.column + 1))
        else:
            error('YAML parser error in file %s: %s\n' % (config_path, e))
        sys.exit(1)

    fontname = config.get('font', {}).get('fontname', None)
    if not fontname:
        error('Error: cannot find "font: fontname" in file %s\n' % config_path)
        sys.exit(1)

    glyphs = [g for g in config.get('glyphs', {}) if g.get('code', None)]

    # validate config: 'code:' codes
    dups = get_dups([g['code'] for g in glyphs])
    if len(dups) > 0:
        error("Error in file %s: glyph codes aren't unique:\n" % config_path)
        for k in sorted(dups.keys()):
            error("Duplicate 'code:' 0x%04x\n" % k)
        sys.exit(1)

    try:
        path = "%s/%s.ttf" % (fonts_dir, fontname)
        font = fontforge.open(path)
    except:
        sys.exit(1)

    # set font encoding so we can select any unicode code point
    font.encoding = 'UnicodeFull'

    glyphs_list = []
    for g in glyphs:
        try:
            font[g['code']]
        except TypeError:
            error("Warning: no such glyph in the source font (code=0x%04x)\n" %
                g['code'])
            continue
        glyphs_list.append(g)

    font = config.get('font', {})
    font.update({'id': i, 'glyphs': glyphs_list})
    return font

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Embedded fonts builder')
    parser.add_argument('config', nargs='+', type=str,
        help='Config example: src/font1/config.yml src/font2/config.yml')
    parser.add_argument('-i', '--fonts_dir', type=str, required=True,
        help='Input fonts directory')
    parser.add_argument('-o', '--dst_file',  type=str, required=True,
        help='Output js file')
    parser.add_argument('-j', '--json', action='store_true', required=False,
        help='Output file in json format instead of js')

    args = parser.parse_args()

    js = ''

    if not args.json:
        js = 'module.exports = ['

    fonts = []
    for i, config in enumerate(args.config):
        font = get_font(i, config, args.fonts_dir)
        for glyph in font['glyphs']:
          if not glyph.has_key('css'):
            glyph['css'] = glyph['file']
        fonts.append(font)

    json_string = json.dumps(fonts, indent=2, separators=(',', ': '))

    if not args.json:
        json_string = json_string.replace('\n', '\n  ') # fixing indent

    js += json_string

    if not args.json:
        js += '];'
    try:
        open(args.dst_file, 'w').write(js)
    except:
        error('Cannot write to file %s\n' % args.dst_file)
        sys.exit(1)

    sys.exit(0)