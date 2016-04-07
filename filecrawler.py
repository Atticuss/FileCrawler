#! python2

from os import walk, path
from operator import itemgetter
import sys, getopt, re, argparse



parser = argparse.ArgumentParser(description='Do stuff with files.', prog='Filecrawler.py', usage='%(prog)s [-h, -r, -v, -p, -c, -t, -z, -e <extension(s)>, -o <filename>] -s|-l [<searchterm>] -d|-f <directory|filename>', \
	formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=65, width =150))
group = parser.add_mutually_exclusive_group(required=True)
parser.add_argument("-r", "--recursive", action='store_false', help="Do not recursively search all files in the given directory")
parser.add_argument("-v", "--verbose", action='store_true', help="Turn on (extremely) verbose mode")
parser.add_argument("-e", "--extension", nargs='?', default=None, help="filetype(s) to restrict search to. seperate lists via commas with no spaces")
parser.add_argument("-l", "--linecount", action='store_true', help="only perform a linecount. restrict filetypes via the -e flag. may override the -s flag.")
parser.add_argument("-p", "--printout", action='store_true', help="print the lines found containing search term")
parser.add_argument("-c", "--casesensitive", action="store_true", help="make search case sensitive")
parser.add_argument("-o", "--output", nargs='?', default=None, help="specify output file. NOTE: will overwrite file if it currently exists")
group.add_argument("-d", "--directory", default=None, help="directory to search")
group.add_argument("-f", "--file", default=None, help="file to search")
parser.add_argument("-s", "--search", default=None, help="term to search for; regex is accepted")
parser.add_argument("-t", "--filetypecount", action='store_true', help="print all file types found with the number of occurrences")
parser.add_argument("-z", "--disableerrorhandling", action='store_true', help="disable error handling to see full stack traces on errors")
args = parser.parse_args()

rec = verbose = pr = case = fcount = rcount = typecount = linecount = errorhandling = 0
term = tosearch = type = extfilter = outfile = None
# extlist = {extension: [fcount, lcount]}
extlist={}
lockedfiles=[]

def main():
	global term, tosearch, type, rec, verbose, extfilter, pr, case, outfile, linecount, typecount, errorhandling
	
	if args.directory != None:
		tosearch = args.directory
		type = 'd'

	elif args.file != None:
		tosearch = args.file
		type = 'f'
			
	if args.extension != None:
		extfilter = args.extension.split(',')
		for i,e in enumerate(extfilter):
			if e[0] != '.':
				extfilter[i] = '.'+e

	rec = args.recursive
	verbose = args.verbose
	case = args.casesensitive

	if args.printout:
		pr = 1

	linecount = args.linecount
	typecount = args.filetypecount
	errorhandling = args.disableerrorhandling
	term = args.search
	outfile = args.output

	if (((type != None) and (tosearch != None)) or linecount or typecount):
		if errorhandling:
			start()
		else:
			try:
				start()
			except:
				printline('[!] An error ocurred:\n')
				for e in sys.exc_info():
					printline(e)
				printline('[*] Note that this script may break on some filetypes when run with 3.4. Please use 2.7')
	elif help != 1:
			print('USAGE:\tfilecrawler.py [-h, -r, -v, -p, -c, -t, -z, -l, -e <extension(s)>, -o <filename>, -s <searchterm>] -d|-f <directory|filename>')
			
def start():
	global term, term, tosearch, rec, linecount, typecount, types, extfilter, outfile, lockedfiles
	loc = 0
	if outfile != None:
		with open(outfile, 'w') as f:
				f.write("") 
	
	#Print intro messages
	printline('\n\t\t --TODO--\n')
	if type == 'd' and rec:
		printline('[*] Recursively running against directory:\n\t%s' % tosearch)
	elif type == 'd' and not rec:
		printline('[*] Non-recursively running against directory:\n\t%s' % tosearch)
	elif type == 'f':
		printline('[*] Running against file:\n\t%s' % tosearch)
	if term != None:
		printline('[*] Searching for:\n\t%s' % term)
	if linecount:
		printline('[*] Performing line count')
	if typecount and extfilter == None:
		printline('[*] Enumerating all found file types')
	if extfilter != None:
		printline('[*] Filtering against the following file extensions:')
		for e in extfilter:
			printline('\t%s' % e)
	if outfile != None:
		printline('[*] Output written to file:\n\t%s' % outfile)        
		
	#Determine appropriate search
	printline('\n\t\t--RESULTS--\n')
	if type == 'd':
		parsedirectory(tosearch)
	elif type == 'f':
		searchfile(tosearch)
	
	for i in extlist.keys():
			loc += extlist.get(i)[1]

	#Print appropriate results
	if term != None:
		printline('\n[*] Search complete. %s lines searched across %s files with %s occurrences found.' % (prettynumbers(loc), prettynumbers(fcount), prettynumbers(rcount)))
	if linecount:
		printline('[*] %s lines parsed across %s files' % (prettynumbers(loc), prettynumbers(fcount)))
	if len(lockedfiles) > 0:
		printline('\n[!] Unable to open the following files:')
		for f in lockedfiles:
			printline('\t%s'%f)
		printline('\n[*] Note: Hidden files are unable to be opened via Python on Windows; please unhide all files you wish to scan.')
	if typecount:
		if extfilter:
			printline('[*] Number of occurrences of filtered file extensions:')
		else:
			printline('[*] %s file types were discovered:' % prettynumbers(len(extlist)))
		
		sorted_extlist = extlist.keys()
		sorted_extlist.sort()

		if linecount:
			printline('\t%s %s %s' % ("Type".ljust(18), "Count".ljust(8), "LoC".ljust(8)))
			for e in sorted_extlist:
				printline('\t%s %s %s' % (e.ljust(18), prettynumbers(extlist.get(e)[0]).ljust(8), prettynumbers(extlist.get(e)[1]).ljust(8)))
		else:
			printline('\t%s %s' % ("Type".ljust(18), "Count".ljust(8)))
			for e in sorted_extlist:
				printline('\t%s %s' % (e.ljust(18), prettynumbers(extlist.get(e)[0]).ljust(8)))

		
def searchfile(file, fext):
	global term, pr, tosearch, rcount, fcount, lockedfiles, extlist
	count = 1
	fcount+=1
	mObj=None
	lcount = extlist.get(fext, [1,0])
	vprint('[?] Searching %s for %s' % (file, term))
	
	try:
		with open(file,'r') as f:
			for line in f:
				lcount[1]+=1
				if case and term:
					mObj = re.search(term, line, flags=0)
				elif term:
					mObj = re.search(term, line, flags=re.IGNORECASE)

				if mObj:
					printline('[*] Line %d in file %s' % (count, file[len(tosearch):]))
					rcount+=1
					if pr:
						if len(line)>200:
							printline(line.strip(' \t\r\n')[:200] + "...\n")
						else:
							printline(line.strip(' \t\r\n') + "\n")
				count+=1
	except IOError:
		lockedfiles.append(file)
		vprint('[?] IOError thrown opening: %s'%file)
	
	extlist[fext] = lcount
	vprint('[?] Number of lines: %d' % count)
	
def searchfiles(files, dir):
	global extfilter, typelist, term
	found = False
	vprint('[?] Searching file list')
	
	for file in files:
		vprint('[?] Parsing file:\t%s'%file)
		fext = path.splitext(file)[1]   
		if len(fext) < 1:
			fext = 'no ext'
			
		if typecount and (extfilter == None or fext in extfilter):
			if fext in extlist.keys():
				inc = extlist.get(fext)
				extlist[fext] = [inc[0]+1, inc[1]]
			else:
				extlist[fext] = [1,0]

		if (term != None or linecount) and (extfilter == None or (extfilter != None and fext in extfilter)):
			searchfile(dir+'/'+file, fext)

def parsedirectory(dir):
	global rec
	flist = []
	dlist = []
	
	vprint('[?] Parsing %s' % dir)
	
	for (dirpath, dirname, filenames) in walk(dir):
		flist.extend(filenames)
		dlist.extend(dirname)
		break
		
	vprint('[?] Files found:')
	vprint(flist)
	vprint('[?] Directories found:')
	vprint(dlist)

	searchfiles(flist, dir)
	
	if (rec) & (dlist != []):
		for d in dlist:
			parsedirectory(dir+'/'+d)
			
def vprint(str):
	global verbose
	if verbose:
		printline(str)

def printline(s):
	print(s)
	if outfile != None:
		with open(outfile, 'a') as f:
			f.write(str(s)+"\n")
			
def prettynumbers(str):
	return "{:,}".format(str)
	
if __name__ == "__main__":
	main()
