#! python2

from os import walk, path
import sys
import re
import argparse
import binascii


class FileCrawler:

    def __init__(self):
        # self.file_stats = {extension: (typecount, number of lines)}
        self.fcount = 0
        self.rcount = 0
        self.lcount = 0
        self.file_stats = {}
        self.lockedfiles = []
        self.magic_numbers = {
            "tarz": b'1F9D',
            "tar": b'1FA0',
            "bz2": b'425A68',
            "DOS-exe": b'4D5A',
            "zip": b'504B0304',
            'rar': b'526172211A0700',
            'rar5': b'526172211A070100',
            'elf': b'7F454C46',
            'png': b'89504E470D0A1A0A',
            'pdf': b'25504446',
            'ms-office': b'D0CF11E0A1B11AE1',
            'dmg': b'7801730D626260',
            '7z': b'377ABCAF271C',
            'gz': b'1F8B',
            'xml': b'3C3F786D6C20'
        }
        parser = argparse.ArgumentParser(description='Do stuff with files.',
                                         prog='Filecrawler.py',
                                         usage=('%(prog)s [-h, -r, -v, -p, -c, -t, -z,'
                                                ' -e <extension(s)>, -o <filename>]'
                                                ' -s|-l [<searchterm>]'
                                                ' -d|-f <directory|filename>'),
                                         formatter_class=(lambda prog:
                                                          argparse.HelpFormatter(prog,
                                                                                 max_help_position=65,
                                                                                 width=150)))
        group = parser.add_mutually_exclusive_group(required=True)
        parser.add_argument("-r", "--recursive", action='store_false',
                            help="Do not recursively search all files in the given directory")
        parser.add_argument("-v", "--verbose", action='store_true',
                            help="Turn on (extremely) verbose mode")
        parser.add_argument("-e", "--extension", nargs='?', default=None,
                            help="filetype(s) to restrict search to. seperate lists"
                            " via commas with no spaces")
        parser.add_argument("-l", "--linecount", action='store_true',
                            help="only perform a self.linecount. restrict filetypes"
                            " via the -e flag. may override the -s flag.")
        parser.add_argument("-p", "--printout", action='store_true',
                            help="print the lines found containing search self.term")
        parser.add_argument("-c", "--casesensitive",
                            action="store_true", help="make search case sensitive")
        parser.add_argument("-o", "--output", nargs='?', default=None,
                            help="specify output file. NOTE: will overwrite file if"
                            " it currently exists")
        group.add_argument("-d", "--directory", default=None,
                           help="directory to search")
        group.add_argument("-f", "--file", default=None, help="file to search")
        parser.add_argument("-s", "--search", default=None,
                            help="term to search for; regex is accepted")
        parser.add_argument("-t", "--filetypecount", action='store_true',
                            help="print all file types found with the number of occurrences")
        parser.add_argument("-z", "--disableerrorhandling", action='store_true',
                            help="disable error handling to see full stack traces on errors")
        args = parser.parse_args()

        # Process arguments
        if args.directory is not None:
            self.tosearch = args.directory
            self.i_type = 'd'

        elif args.file is not None:
            self.tosearch = args.file
            self.i_type = 'f'

        if args.extension is not None:
            self.extfilter = args.extension.split(',')
            for i, e in enumerate(self.extfilter):
                if e[0] != '.':
                    self.extfilter[i] = '.' + e
        else:
            self.extfilter = None
        self.rec = args.recursive
        self.verbose = args.verbose
        self.case = args.casesensitive
        self.print_out = 0

        if args.printout:
            self.print_out = 1

        self.linecount = args.linecount
        self.typecount = args.filetypecount
        self.errorhandling = args.disableerrorhandling
        self.term = args.search
        self.outfile = args.output

    def main(self):
        if (((self.i_type is not None) and (self.tosearch is not None)) or
                self.linecount or self.typecount):
            if self.errorhandling:
                self.start()
            else:
                try:
                    self.start()
                except:
                    self.printline('[!] An error ocurred:\n')
                    for e in sys.exc_info():
                        self.printline(e)
                    self.printline(
                        '[*] Note that this script may break on some filetypes'
                        ' when run with 3.4. Please use 2.7')

    def start(self):
        loc = 0

        # Print intro messages
        print('\n\t\t --TODO--\n')
        if self.i_type == 'd' and self.rec:
            print('[*] Recursively running against directory:\n\t%s' %
                  self.tosearch)
        elif self.i_type == 'd' and not self.rec:
            print('[*] Non-self.recursively running against directory:\n\t%s' %
                  self.tosearch)
        elif self.i_type == 'f':
            print('[*] Running against file:\n\t%s' % self.tosearch)
        if self.term is not None:
            print('[*] Searching for:\n\t%s' % self.term)
        if self.linecount is not None:
            print('[*] Performing line count')
        if self.typecount and self.extfilter is None:
            print('[*] Enumerating all found file types')
        if self.extfilter is not None:
            print('[*] Filtering against the following file extensions:')
            for e in self.extfilter:
                print('\t%s' % e)
        if self.outfile is not None:
            print('[*] Output written to file:\n\t%s' % self.outfile)

        # Determine appropriate search
        self.printline('\n\t\t--RESULTS--\n')
        if self.i_type == 'd':
            self.parsedirectory(self.tosearch)
        elif self.i_type == 'f':
            self.searchfile(self.tosearch)
        for i in self.file_stats.keys():
            loc += self.file_stats.get(i)[1]

        # Print appropriate results
        if self.term is not None:
            self.printline('\n[*] Search complete. %s lines searched across %s'
                           ' files with %s occurrences found.' %
                           (self.prettynumbers(loc),
                            self.prettynumbers(self.fcount),
                            self.prettynumbers(self.rcount)))
        if self.linecount:
            self.printline('[*] %s lines parsed across %s files' %
                           (self.prettynumbers(loc), self.prettynumbers(self.fcount)))
        if len(self.lockedfiles) > 0:
            self.printline('\n[!] Unable to open the following files:')
            for f in self.lockedfiles:
                self.printline('\t%s' % f)
            self.printline(
                '\n[*] Note: Hidden files are unable to be opened'
                ' via Python on Windows; please unhide all files you wish to scan.')
        if self.typecount:
            if self.extfilter:
                self.printline(
                    '[*] Number of occurrences of filtered file extensions:')
            else:
                self.printline('[*] %s file types were discovered:' %
                               self.prettynumbers(len(self.file_stats.keys())))

            ext_list = self.file_stats.keys()
            ext_list.sort()

            if self.linecount:
                self.printline("\t%s %s %s" %
                               ("Type".ljust(18), "Count".ljust(8), "LoC".ljust(8)))
                for e in ext_list:
                    self.printline('\t%s %s %s' %
                                   (e.ljust(18),
                                    self.prettynumbers(self.file_stats.get(e)[0]).ljust(8),
                                    self.prettynumbers(self.file_stats.get(e)[1]).ljust(8)))
            else:
                self.printline("\t%s %s" %
                               ("Type".ljust(18), "Count".ljust(8)))
                for e in ext_list:
                    self.printline('\t%s %s' % (e.ljust(18), self.prettynumbers(
                        self.file_stats.get(e)[0]).ljust(8)))

    def searchfile(self, file, fext=None):
        count = 1
        self.fcount += 1
        m_obj = None
        self.lcount = self.file_stats.get(fext, [1, 0])

        self.vprint('[?] Searching %s for %s' % (file, self.term))

        try:
            with open(file, 'r') as f:
                lines = f.readlines()
            if self.term:
                for line in lines:
                    self.lcount[1] += 1
                    if self.case and self.term:
                        m_obj = re.search(self.term, line, flags=0)
                    elif self.term:
                        m_obj = re.search(self.term, line, flags=re.IGNORECASE)

                    if m_obj:
                        self.printline('[*] Line %d in file %s' %
                                       (count, file[len(self.tosearch):]))
                        self.rcount += 1
                        if self.print_out:
                            if len(line) > 200:
                                self.printline(line.strip(
                                    ' \t\r\n')[:200] + "...\n")
                            else:
                                self.printline(line.strip(' \t\r\n') + "\n")
                    count += 1
            else:
                self.lcount[1] += len(lines)
        except IOError:
            self.lockedfiles.append(file)
            self.vprint('[?] IOError thrown opening: %s' % file)

        self.file_stats[fext] = self.lcount
        self.vprint('[?] Number of lines: %d' % count)

    def get_magic(self, infile):
        # Attempt to read magic bytes. If in common dict set ext appropriately
        with open(infile, 'rb') as f:
            mbytes = f.read(16)
        for k, v in self.magic_numbers.iteritems():
            if mbytes.startswith(binascii.unhexlify(v)):
                return k.upper()
        self.vprint("[?] Magic Numbers for File: %s\n%s" % (infile, mbytes))
        return None

    def searchfiles(self, files, i_dir):
        self.vprint('[?] Searching file list')

        for file in files:
            self.vprint('[?] Parsing file:\t%s' % file)
            fext = path.splitext(file)[1]
            if len(fext) < 1:
                t_ext = self.get_magic(i_dir + "/" + file)
                if t_ext is not None:
                    fext = t_ext
                else:
                    fext = 'no ext'

            if self.typecount is not None and (self.extfilter is None or
                                               fext in self.extfilter):
                if fext in self.file_stats.keys():
                    inc = self.file_stats.get(fext)
                    self.file_stats[fext] = [inc[0] + 1, inc[1]]
                else:
                    self.file_stats[fext] = [1, 0]

            if ((self.term is not None or self.linecount) and
                    (self.extfilter is None or
                     (self.extfilter is not None and fext in self.extfilter))):
                self.searchfile(i_dir + '/' + file, fext)

    def parsedirectory(self, i_dir):
        flist = []
        dlist = []

        self.vprint('[?] Parsing %s' % i_dir)

        for (_, dirname, filenames) in walk(i_dir):
            flist.extend(filenames)
            dlist.extend(dirname)
            break

        self.vprint('[?] Files found:')
        self.vprint(flist)
        self.vprint('[?] Directories found:')
        self.vprint(dlist)

        self.searchfiles(flist, i_dir)

        if (self.rec) & (dlist != []):
            for d in dlist:
                self.parsedirectory(i_dir + '/' + d)

    def vprint(self, o_str):
        if self.verbose:
            self.printline(o_str)

    def printline(self, o_str):
        if self.outfile is not None:
            with open(self.outfile, 'a') as o_file:
                o_file.write(str(o_str) + "\n")
        else:
            print(o_str)

    @staticmethod
    def prettynumbers(o_str):
        return "{:,}".format(o_str)

if __name__ == "__main__":
    f_crawl = FileCrawler()
    f_crawl.main()
