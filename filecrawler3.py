#! python3
#evenr sourcing, xmpp, homekit
from os import walk, path
from collections import OrderedDict
import sys, getopt, re, argparse, threading, queue, time



parser = argparse.ArgumentParser(description='Do stuff with files.', prog='filecrawler.py', usage='%(prog)s [-h, -r, -v, -p, -c, -t, -z, -e <extension(s)>, -o <filename>] -s|-l [<searchterm>] -d|-f <directory|filename>', \
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
group.add_argument("-f", "--file", default=None, help="file to search. single threaded only.")
parser.add_argument("-s", "--search", default=None, help="term to search for; regex is accepted")
parser.add_argument("-t", "--filetypecount", action='store_true', help="print all file types found with the number of occurrences")
parser.add_argument("-z", "--disableerrorhandling", action='store_true', help="disable error handling to see full stack traces on errors")
parser.add_argument("-n", "--numthreads", nargs='?', help="number of threads to use. default is 5.")
args = parser.parse_args()

settings = {}
results = {
    'lcount' : 0,
    'fcount' : 0,
    'rcount' : 0,
    'printline' : None,
    'extlist' : {}
}

searchQueue = queue.Queue()
resultQueue = queue.Queue()

def main():
    global settings
    
    if args.numthreads:
        settings['numthreads'] = int(args.numthreads)
    else:
        settings['numthreads'] = 5

    if args.directory:
        settings['type'] = 'd'
        settings['tosearch'] = args.directory

    elif args.file:
        settings['type'] = 'f'
        settings['tosearch'] = args.file
        settings['numthreads'] = 1
            
    if args.extension:
        extfilter = args.extension.split(',')
        for i,e in enumerate(extfilter):
            if e[0] != '.':
                extfilter[i] = '.'+e
        settings['extfilter'] = extfilter

    settings['rec'] = args.recursive
    settings['verbose'] = args.verbose
    settings['case'] = args.casesensitive

    if args.printout:
        settings['pr'] = 1

    settings['linecount'] = args.linecount
    settings['typecount'] = args.filetypecount
    settings['errorhandling'] = args.disableerrorhandling
    settings['term'] = args.search
    settings['outfile'] = args.output

    if (((settings['type'] != None) and (settings['tosearch'] != None)) or settings['linecount'] or settings['typecount']):
        if settings['errorhandling']:
            start()
        else:
            try:
                start()
            except:
                printline('[!] An error ocurred:\n')
                for e in sys.exc_info():
                    printline(e)
    elif help != 1:
            print('USAGE:\tfilecrawler.py [-h, -r, -v, -p, -c, -t, -z, -l, -e <extension(s)>, -o <filename>, -s <searchterm>] -d|-f <directory|filename>')
            
def start():
    global settings, results

    if settings['outfile'] != None:
        with open(settings['outfile'], 'w') as f:
                f.write("") 
    
    #Print intro messages
    printline('\n\t\t --TODO--\n')
    if settings['type'] == 'd' and settings.get('rec',None):
        printline('[*] Recursively running against directory:\n\t%s' % settings['tosearch'])
    elif settings['type'] == 'd' and not settings.get('rec',None):
        printline('[*] Non-recursively running against directory:\n\t%s' % settings['tosearch'])
    elif settings['type'] == 'f':
        printline('[*] Running against file:\n\t%s' % settings['tosearch'])
    if settings.get('term', None):
        printline('[*] Searching for:\n\t%s' % settings['term'])
    if settings.get('linecount',None):
        printline('[*] Performing line count')


    if settings.get('typecount',None) and not settings.get('extfilter',None):
        printline('[*] Enumerating all found file types')
    if settings.get('extfilter',None):
        printline('[*] Filtering against the following file extensions:')
        for e in settings['extfilter']:
            printline('\t%s' % e)
    if settings.get('outfile',None):
        printline('[*] Output written to file:\n\t%s' % settings['outfile'])        
        
    #Dump all files (via their path) into queue. start up threads and wait until they are done.
    buildQueue()

    threads = [Parser(searchQueue,resultQueue,settings,id) for id in range(settings['numthreads'])]
    [t.start() for t in threads]

    while not checkIfDone(threads):
        handleResults()
    
    #Print appropriate results
    printline('\n\t\t--RESULTS--\n')
    if settings.get('term',None):
        printline('[*] Search complete. %s lines searched across %s files with %s occurrences found.' % (prettynumbers(results['lcount']), prettynumbers(results['fcount']), prettynumbers(results['rcount'])))
    if settings.get('linecount',None):
        printline('[*] %s lines parsed across %s files' % (prettynumbers(results['lcount']), prettynumbers(results['fcount'])))
    if settings.get('typecount',None):
        if settings.get('extfilter',None):
            printline('[*] Number of occurrences of filtered file extensions:')
        else:
            printline('[*] %s file types were discovered:' % prettynumbers(len(results.get('extlist',None))))
        for e in sorted(results['extlist'].items()):
            printline('\t%s %s' % (e[0].ljust(18), prettynumbers(e[1]).ljust(8)))
            
def buildQueue():
    global settings,results

    if settings['type'] == 'd':
        for (dirpath,dirname,filenames) in walk(settings['tosearch']):
            for filename in filenames:
                fext = path.splitext(filename)[1]
                if len(fext) == 0:
                    fext = 'no ext'
                if not settings.get('extfilter',None) or fext in settings['extfilter']:
                    results['extlist'][fext] = results['extlist'].get(fext,0) + 1
                    searchQueue.put('%s/%s'%(dirpath,filename))
                    results['fcount'] += 1
                    if settings.get('typecount',None):
                        results['extlist'][fext] = results['extlist'].get(fext,0) + 1
    else:
        searchQueue.put(settings['tosearch'])

def checkIfDone(threads):
    for t in threads:
        if t.isAlive():
            return False
    return True

def handleResults():
    global results
    while not resultQueue.empty():
        resultType,data = resultQueue.get()
        if resultType == 'rcount':
            results['rcount'] += data
        elif resultType == 'lcount':
            results['lcount'] += data
        elif resultType == 'fcount':
            print('[*] increasing fcount')
            results['fcount'] += data
        elif resultType == 'printline':
            printline(data)
        elif resultType == 'vprint':
            vprint(data)

def vprint(str):
    global settings

    if settings.get('verbose',None) == True:
        printline(str)

def printline(s):
    global settings
    print(s)
    if settings.get('outfile',None):
        with open(settings['outfile'], 'a') as f:
            f.write(str(s)+"\n")
            
def prettynumbers(str):
    return "{:,}".format(str)

class Parser(threading.Thread):
    def __init__(self,searchQueue,resultQueue,settings,id):
        threading.Thread.__init__(self)
        self.searchQueue = searchQueue
        self.resultQueue = resultQueue
        self.settings = settings
        self.done = False
        self.id = id

    def run(self):
        #print('thread %s running'%self.id)
        while not self.done and not self.searchQueue.empty():
            tosearch = searchQueue.get()
            self.resultQueue.put(('vprint','[*] thread %s searching: %s'%(self.id,tosearch)))

            lcount = 0
            mObj = None

            with open(tosearch,'br') as f:
                for line in f:
                    try:
                        line = line.decode('utf-8')

                        if self.settings.get('case',None) and self.settings.get('term',None):
                            mObj = re.search(self.settings['term'], line, flags=0)
                        elif self.settings.get('term',None):
                            mObj = re.search(self.settings['term'], line, flags=re.IGNORECASE)

                        if mObj:
                            res = '[*] Line %d in file %s' % (lcount, tosearch)
                            if self.settings.get('pr',None):
                                if len(line)>200:
                                   res += '\n%s...\n'%line.strip(' \t\r\n')[:200]
                                else:
                                    res += '\n%s\n'%line.strip(' \t\r\n')
                            self.resultQueue.put(('printline',res))
                            self.resultQueue.put(('rcount',1))
                    except UnicodeDecodeError:
                        continue
                    lcount += 1
            self.resultQueue.put(('lcount',lcount))
    
if __name__ == "__main__":
    main()
