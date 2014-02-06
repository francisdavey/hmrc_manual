hmrc_manual
===========

Scrapes and sanitises HMRC manuals

The HMRC manuals are not particularly easy to read online. For example see the [Employee Share Schemes Unit Manual](http://www.hmrc.gov.uk/manuals/essum/index.htm). 

The python script build.py will scrape and parse two manuals at the moment (the ESSUM and the VCM manuals) but it should be obvious how to add new ones. It outputs a single .html file (for easy searching/reading) and a .epub.
