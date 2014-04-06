# This module understands the a number of HMRC manuals and parses them it into
# a structure

import urllib2
import re
import base64
import os.path
import urlparse
import zipfile
import sys

def rna(s): return "".join(filter(lambda x: ord(x)<128, s))

def prin(s):
    s=rna(s)
    #print(s)

def fix_title(url, title):
    if re.search("vatrevchgmanual/index\.htm", url):
        return("VATREVCHG - Reverse charge: Contents")
    else:
        return(title)

#ogl='''<a href="http://www.nationalarchives.gov.uk/doc/open-government-licence/">Contains public sector information licensed under the Open Government Licence v1.0.</a>'''
#base='''http://www.hmrc.gov.uk/manuals/essum/Index.htm'''

#footer='''<footer>This is an unofficial version derived from HMRC's <a href="{base}">online ESSUM manual</a>. {ogl}'''.format(base=base, ogl=ogl)

def xhtml_wrap(body, title=''):
    s='''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
    "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html version="-//W3C//DTD XHTML 1.1//EN"
      xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"
      >
<head>
<title>{title}</title>
<body>{body}
</body>
</html>'''.format(body=body, title=title)
    return(s)

def html_wrap(body, title=''):
    s='''<!DOCTYPE html>
<html lang="en">
<head>
<title>{title}</title>
<meta charset="utf-8" />
</head>
<body>
{body}
</body>
</html>'''.format(body=body, title=title)
    return(s)

def clean_title(s):
    (s, N)=re.subn('(?i)(<p>|</p>)', '', s)
    s=s.strip('\n')
    return(s)

# Statutes are referenced in abbreviated form.
# Examples:

# TCGA92/S150A
# ITA07/Part 5
# ITA07/Part 5A
# TCGA92/SCH5B
# TCGA92/Schedule 5C
# ITA07/Part4/Chapter 6
# ITA07/S192 to S199 and S303 to 310


statutory_reference_table={
    'ITA07' : "http://www.legislation.gov.uk/ukpga/2007/3",
    'TCGA92' : "http://www.legislation.gov.uk/ukpga/1992/12",
    'CTA10' : "http://www.legislation.gov.uk/ukpga/2010"
}

doc_reference_table={
    'Notice 735' : "http://customs.hmrc.gov.uk/channelsPortalWebApp/channelsPortalWebApp.portal?_nfpb=true&_pageLabel=pageLibrary_ShowContent&id=HMCE_PROD1_028649&propertyType=document"#,
#    'Value Added Tax (Section 55A)(Specified goods and services and excepted supplies) Order 2010' : "http://www.legislation.gov.uk/uksi/2010/2239/made"
    }

def substitute_single_statutory_reference(mobj):
    return '''<a href="{0}">{1}</a>'''.format(statutory_reference_table[mobj.group(1)], mobj.group(1))

def substitute_statutory_references(s):
    statutory_references=statutory_reference_table.keys()
    (result, N)=re.subn('(?i)({})'.format('|'.join(statutory_references)), substitute_single_statutory_reference, s)
    return result

def substitute_doc_references(s):
    for key in doc_reference_table:
        #print(key)
        value=doc_reference_table[key]
        key_pattern_string=key.replace(" ", ".*?")
        (s, N)=re.subn(key_pattern_string, '''<a href="{}">{}</a>'''.format(value, key), s, re.I)
        #print(N)
        #print(re.search('(?i)735 VAT', s))
        #print(s)
    return(s)

def tidy(s):
    result=[]
    #s=re.sub("(?mis)<br><p>", "<p>", s)
    (s, N1)=re.subn("(?is)<br>(\s*<table.*?</table>\s*)(<br>)?", r"\1", s)
    (s, N2)=re.subn("^\s*<br>|<br>\s*$", '', s) # remove <br> at beginning and end
    pat=re.compile("(?mis)(<p>|<br>)(.*?)(</p>|<br>)")
    mobj=pat.search(s)
    while mobj:
        result.append(s[:mobj.start()])
        result.append('''<p>{0}</p>\n'''.format(mobj.group(2)))
        s=s[mobj.end():]
        mobj=pat.search(s)
    s="".join(result)

    (s, N3)=re.subn("(?mis)(<p>)(\s|\n)*(<p>)", "<p>", s)
    (s, N4)=re.subn("(?is)<a[^>]*>top.of.page</a>", "",  s)
    (s, N5)=re.subn('''(?is)(<a[^>]*href=")([A-Z]+[0-9]+)\.htm"''', '''\\1#\\2"''', s)
    #s=re.sub("(?mis)(<p>)(\s*)(<p>)
    s=substitute_statutory_references(s)
    s=substitute_doc_references(s)
    return "".join(s)

def correct_hyperlinks(s):
    apat=re.compile('''<a\s*href="([^"]*)"''')

class Page(object):
    def __init__(self, url, title, base, level=0):
        self.url=url
        self.title=title
        self.level=level
        self.base=base
        self.ref=self.url.split('/')[-1].split('.')[0]
        self.contents_page=False
        self.content=None
        # debugging
        if self.base==1:
            print(self.url, self.title, self.base, self.level)
            raise Exception

    def recurse(self):
        if self.contents_page:
            for (ref, link, title) in self.contents:
                prin(ref)
                if re.search('home.htm', link):
                    continue
                #print("self.base={}, link={}, level={}".format(self.base, link, self.level))
                D=get_page(urlparse.urljoin(self.base, link), self.base, self.level)
                D.recurse()
                self.children[ref]=D
#
#    def to_html(self, base):
#        if self.contents_page:
#            for (ref, link, title):
#                
        
class Contents(Page):
    def __init__(self, url, title, base, level=0):
        super(Contents, self).__init__(url, title, base, level)
        #self.url=url
        #self.title=title
        self.contents_page=True
        self.contents=[]
        self.dict={}
        self.children={}

    def add(self, ref, link, title):
        self.contents.append( (ref, link, title))
        self.dict[ref]=(link, title)

    def html(self, split_level=1):
        prin("HTML call on {0}, at level {1}, link={2}".format(self.ref, self.level, self.url))
        if self.level==split_level:
            result=[] 
            for (ref, link, title) in self.contents:
                prin("@{0}, {1}, {2}".format(ref, link, title))
                result.append((ref, title, self.children[ref].html(split_level)))
            return(result)
        else:
            result=[]
#            result.append('''<h{height} id="{ref}">[{level}] {title}</h{height}>'''.format(level=self.level, title=self.title, height=self.level, ref=self.ref))
            for (ref, link, title) in self.contents:
                result.append('''<h{height} id="{ref}">{title}</h{height}>'''.format(level=self.level, title=title, height=self.level, ref=ref))
                #result.append('''<h{height} id="ref">[/{level}] {title}</h{height}>'''.format(level=self.level, title=title, height=self.level, ref=ref))
                prin("ref=[[{0}]], link={1}, title={2}".format(ref, link, title))
                #html=self.children[ref].html(split_level)
                result.append(self.children[ref].html(split_level))
            return '\n'.join(result)
            

class Leaf(Page):
    def __init__(self, url, title, base, level=0):
        super(Leaf, self).__init__(url, title, base, level)
        #self.url=url
        #self.title=title
        #self.contents_page=False
        #self.content=None

    def html(self, split_level):
        return(tidy(self.content))

def get_page(url, base, level=0):
    '''Downloads a page (if there is no local copy) then parses it
    depending on whether it is a contents page or a content page.'''

    # debugging
    if base==1:
        print(url, base, level)
        raise Exception


    burl=base64.urlsafe_b64encode(url)
    bfile=os.path.join('downloaded', burl)
    if os.path.exists(bfile):
        bstream=open(bfile, 'r')
        html=bstream.read()
        bstream.close()
    else:
        response=urllib2.urlopen(url)
        html=response.read()
        bstream=open(bfile, 'w')
        bstream.write(html)
        bstream.close()

    #print(url)
    #print('##{0}\n{1}'.format(url, html[:128]))
    mobj=re.search('(?is)<h1>(.*?)</h1>', html)
    if mobj is None:
        print("No <h1> title on page at ({}) of length {}:\n{}".format(url, len(html), html[:512]))
        sys.exit(1)
    title=fix_title(url, clean_title(mobj.group(1)))
    html=html[mobj.end():]
    if re.search('(?i)contents\w*$', title):
        X=parse_contents_table(url, title, html, base, level+1)
    else:
        X=parse_page(url, title, html, base, level+1)
    return(X)

def parse_page(url, title, html, base, level):
    '''Parses a normal page and returns a Leaf object.'''

    # debugging
    if base==1:
        print(url, title, base, level)
        raise Exception

    P=Leaf(url, title, base, level)
    #prin(html)
    mobj=re.search('(?is)<div', html)
    P.content=html[:mobj.start()]
    return(P)

def parse_contents_table(url, title, html, base, level):
    '''Parses a contents page and returns a Contents object'''

    # debugging
    if base==1:
        print(url, title,  base, level)
        raise Exception


    C=Contents(url, title, base, level)
    #prin('##{0}\n{1}'.format(url, html[:128]))
    mobj=re.search('(?i)<table (border="0"|class="tableborder(zero)?").*?>', html)
    html=html[mobj.end():]

    end_obj=re.search('(?is).*?(?=</table|$)', html)
    html=html[:end_obj.end()]

    tr=re.compile('(?i)<tr>')
    mobj=tr.search(html)
    html=html[mobj.end():]
    while mobj:
        td=re.compile('<td.*?>(.*?)</td>', re.DOTALL | re.I)
        # handle empty rows here
        #print('##\n' + html[:128])
        col1=td.search(html)
        if col1 is None:
            html=html[mobj.end():]
            mobj=tr.search(html)
            continue

        col_html=html[col1.start():]

        # Handles lines in a contents page where the contents have
        # been withheld under the FOI

        # See eg http://www.hmrc.gov.uk/manuals/vatrevchgmanual/VATREVCHG23000.htm

        if re.search("(?i)This text has been withheld", col_html):
            html=html[mobj.end():]
            mobj=tr.search(html)
            continue

        a=re.compile('<a *href="([^"]*?)" *>(.*?)</a>', re.DOTALL | re.I)
        amatch=a.search(col_html)
        if not amatch:
            print("####",url, col_html, a)
            sys.exit(1)
        ref=amatch.group(2)
        if amatch:
            link=amatch.group(1)
        else:
            link=None
        html=html[col1.end():]

        col2=td.search(html)
        col_html=html[col2.end():]
        title=clean_title(col2.group(1))
        html=html[col2.end():]

        C.add( ref, link, title)

        #prin(ref, link, title)
        mobj=tr.search(html)
        
    return(C)

def make_html(C, title, filename="hmrc.html"):
    html=C.html(split_level=0)
    #tidy_html=tidy(html)
    tidy_html=html
    out=open(filename, 'w')
    out.write(html_wrap(html, title))
    out.close()

def make_epub(C, title, image, short_code):
    # can we do make_epub with a leaf?
    #print(C, type(C))
    R=C.html()
    #epub = zipfile.ZipFile('my_ebook.epub', 'w')
    epub = zipfile.ZipFile('{}_ebook.epub'.format(short_code), 'w')

    spine_list=[]
    manifest_list=[]
    contents_list=[]

    #book_title='HMRC ESSUM Manual'
    book_title=title
    book_language='en-GB'
    
    #title_image_filename='''474px-Somerset_House_Inland_Revenue_entrance.jpg'''
    title_image_filename=image
    image_directory='''images'''

    # The first file must be named "mimetype"
    epub.writestr("mimetype", "application/epub+zip")
    
    # Creating the HTML files.
    # The filenames of the HTML are listed in html_files
    ##html_files = ['foo.html', 'bar.html']
    html_files=[]
    for (key, title, html) in R:
        filename="{0}.xhtml".format(key)
        #tidy_html=tidy(html)
        tidy_html=html
        out=open(filename, 'w')
        out.write(xhtml_wrap(html, title))
        out.close()
        epub.writestr("OEBPS/" + filename, xhtml_wrap(tidy_html))
        html_files.append(filename)
    
    # Creating the title image file
    instream=open(os.path.join(image_directory, title_image_filename), 'rb')
    title_image=instream.read()
    #print(type(title_image))
    #print(len(title_image))
    #print(title_image_filename)
    instream.close()
    epub.writestr(os.path.join('OEBPS', title_image_filename), title_image)
    #print(epub.namelist())

    # title page

    title_page='''<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{title}</title>
  </head>
  <body>
    <h1>{title}</h1>
    <div><img src="{image}" alt="Title page"/></div>
  </body>
</html>'''.format(title=book_title, image=title_image_filename)
    epub.writestr(os.path.join('OEBPS', 'title.html'), title_page)
    manifest_list.append('<item id="cover" href="title.html" media-type="application/xhtml+xml"/>')
    spine_list.append('<itemref idref="cover" linear="no"/>')


    # We need an index file, that lists all other HTML files
    # This index file itself is referenced in the META_INF/container.xml
    # file
    epub.writestr("META-INF/container.xml", '''<container version="1.0"
               xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
      <rootfiles>
        <rootfile full-path="OEBPS/Content.opf" media-type="application/oebps-package+xml"/>
      </rootfiles>
    </container>''');
    
    # The index file is another XML file, living per convention
    # in OEBPS/Content.xml
    index_tpl = '''<package version="2.0"
      xmlns="http://www.idpf.org/2007/opf">
      <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>{title}</dc:title>
        <dc:creator opf:role="aut">HMRC</dc:creator>
        <dc:creator opf:role="edt" opf:file-as="Davey, Francis">Francis Davey</dc:creator>
        <dc:language>{language}</dc:language>
      </metadata>
      <manifest>
        %(manifest)s
      </manifest>
      <spine toc="ncx">
        %(spine)s
      </spine>
    </package>'''.format(title=book_title, language=book_language)

    # table of contents

    i=2
    for (ref, link, title) in C.contents:
        prin("{0}, {1}, {2}".format(ref, link, title))
        contents_list.append('''<navPoint id="navpoint-{count}" playOrder="{count}">
\t<navLabel>
\t\t<text>{title}</text>
\t</navLabel>
<content src="{ref}.xhtml" />
</navPoint>
'''.format(count=i, title=title, ref=ref))
        i=i+1
                           

    ncx='''<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
                 "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid"
content="urn:uuid:0cc33cbd-94e2-49c1-909a-72ae16bc2658"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{title}</text>
  </docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel>
        <text>Book cover</text>
      </navLabel>
      <content src="title.html"/>
    </navPoint>
    {contents}
</ncx>'''.format(title=book_title, contents='\n'.join(contents_list))
    epub.writestr(os.path.join('OEBPS', 'toc.ncx'), ncx)
    manifest_list.append('''<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>''')

    # Write each HTML file to the ebook, collect information for the index
    for i, html in enumerate(html_files):
        basename = os.path.basename(html)
        manifest_list.append('<item id="file_%s" href="%s" media-type="application/xhtml+xml"/>' % (
            i+1, basename))
        spine_list.append('<itemref idref="file_%s" />' % (i+1))
        #epub.write(html, 'OEBPS/'+basename)
    
    manifest="\n".join(manifest_list)
    spine="\n".join(spine_list)

    #print("Spine list:", spine_list)
    #print("Manifest:", manifest)
    #print("HTML files:", html_files)

    # Finally, write the index
    epub.writestr('OEBPS/Content.opf', index_tpl % {
            'manifest': manifest,
            'spine': spine,
            })
            
