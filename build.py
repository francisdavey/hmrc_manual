#!/opt/local/bin/python
import sys
import argparse
import hmrc

PARAM_TABLE={
    "essum" : { 
        "base_url": "http://www.hmrc.gov.uk/manuals/essum/Index.htm",
        "name" : "ESSUM",
        "title" : "HMRC ESSUM Handbook",
        "image" : '''474px-Somerset_House_Inland_Revenue_entrance.jpg'''
        },
    "vcmmanual" : {
        "base_url" : "http://www.hmrc.gov.uk/manuals/vcmmanual/",
        "name" : "VCM",
        "title" : "HMRC Venture Capital Schemes Manual",
        "image" : '''474px-Somerset_House_Inland_Revenue_entrance.jpg'''
        },
    "nimmanual" : {
        "base_url" : "http://www.hmrc.gov.uk/manuals/nimmanual/",
        "name" : "NIM",
        "title" : "National Insurance Manual",
        "image" : '''474px-Somerset_House_Inland_Revenue_entrance.jpg'''
        },
    "vatrevchg" : {
        "base_url" : "http://www.hmrc.gov.uk/manuals/vatrevchgmanual/index.htm",
        "name" : "VATREVCHG",
        "title" : "VAT Reverse Charge Manual",
        "image" : '''474px-Somerset_House_Inland_Revenue_entrance.jpg'''
        },
    "vatsmanual" : {
        "base_url" : "http://www.hmrc.gov.uk/manuals/vatsmanual/index.htm",
        "name" : "VATS",
        "title" : "VAT Single Market",
        "image" : '''474px-Somerset_House_Inland_Revenue_entrance.jpg'''
        }
}

def main(parser_constructor, argv=None):
    if argv is None:
        argv = sys.argv

    parser=parser_constructor(argv)
    args = parser.parse_args(argv[1:])
    #print(args)
    args.func(args)
    #print(parser.parse_args("A".split()))

def parse_arguments(argv):
    parser=argparse.ArgumentParser(prog=argv[0], description="Builds HMRC manuals into more useful forms.")
    parser.add_argument("manual", metavar="manual", help='code for the HMRC manual')
    parser.set_defaults(func=build_manual)

    return parser

def build_manual(args):
    manual_code=args.manual.lower()
    print("Building {}".format(manual_code))
    base=PARAM_TABLE[manual_code]['base_url']
    short_code=PARAM_TABLE[manual_code]['name'].lower()
    title=PARAM_TABLE[manual_code]['title']
    image=PARAM_TABLE[manual_code]['image']

    C=hmrc.get_page(base, base)
    C.recurse()
    hmrc.make_epub(C, title, image, short_code)
    hmrc.make_html(C, title, filename="{}.html".format(manual_code))

if __name__ == "__main__":
    sys.exit(main(parser_constructor=parse_arguments))
