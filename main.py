from pandac.PandaModules import DCFile
import os


CLASS_DELIMITERS = [
    'AI',
    'UD',
    'OV'
]

IMPORTS = {
    # Imports not included in the root folder go here.
    'DistributedObject': 'direct.distributed',
    'DistributedSmoothNode': 'direct.distributed',
    'DistributedObjectGlobal': 'direct.distributed',
}

INDENT = '    '


class DCStubGenerator:
    def __init__(self, filedir):
        self.dcfile = DCFile()
        self.dcfile.read(filedir)
        self.classesTuples = []
        self.dclass2module = {}
        self.className2Fields = {}
        self.className2ImportSymbol = {}
        if not self.dcfile.allObjectsValid():
            print 'There was an error reading the dcfile!'
            return

        for i in xrange(self.dcfile.getNumImportModules()):
            importModule = self.dcfile.getImportModule(i)
            for n in xrange(self.dcfile.getNumImportSymbols(i)):
                symbol = self.dcfile.getImportSymbol(i, n)
                classes = symbol.split('/')
                if len(classes) > 1:
                    for dcClass in classes[1:]:
                        classes[classes.index(dcClass)] = classes[0] + dcClass

                self.classesTuples.append(classes)

                for dcClass in classes:
                    self.dclass2module[dcClass] = importModule

                if importModule.split('.')[0] in ('direct', 'panda3d'):
                    continue

                try:
                    exec('import %s' % importModule)
                except ImportError:
                    self.generateModule(importModule)

        for classes in self.classesTuples:
            for dcClass in classes:
                importModule = self.dclass2module[dcClass]
                importLine = 'from %s import %s' % (importModule, dcClass)

                if importModule.split('.')[0] in ('direct', 'panda3d'):
                    continue

                try:
                    exec(importLine)
                except ImportError:
                    self.generateClass(importModule, dcClass)

        for className in self.classesTuples:
            dcClass = self.dcfile.getClassByName(className[0])
            self.className2Fields[className[0]] = []
            for i in xrange(dcClass.getNumFields()):
                dcField = dcClass.getField(i)
                self.className2Fields[className[0]].append(dcField)

                if self.dclass2module[className[0]].split('.')[0] not in ('direct', 'panda3d'):
                    self.generateField(dcField, className[0])

    def generateModule(self, module):
        modulePath = module.replace('.', '/')

        if not os.path.isdir(modulePath):
            print 'Generating module path %s' % modulePath
            os.makedirs('./' + modulePath)

        os.chdir(modulePath)
        if '.' in module:
            for x in xrange(len(module.split('.'))):
                open('./__init__.py', 'w+')
                os.chdir('..')
        else:
            self.writeInitFile(module)

    def writeInitFile(self, module):
        open('./' + module + '/__init__.py', 'w+')

    def generateClass(self, importModule, className):
        directory = importModule.replace('.', '/')
        f = open(
            directory + '/' + className + '.py', 'w+'
        )
        dcClassName = className

        for classdel in CLASS_DELIMITERS:
            if classdel in className:
                dcClassName = className.split(classdel)[0]

        dcClass = self.dcfile.getClassByName(dcClassName)
        parentClasses =[]
        file = ""
        for i in xrange(dcClass.getNumParents()):
            parentClass = dcClass.getParent(i).getName()

            for classdel in CLASS_DELIMITERS:
                if classdel in className:
                    parentClass += classdel

            if parentClass not in self.dclass2module.keys() and parentClass not in IMPORTS:
                print 'Couldn\'t find defined import %s!' % parentClass
                baseClass = self.removeDelimiter(parentClass)
                if baseClass in IMPORTS:
                    parentModule = IMPORTS.get(baseClass)
                    print 'Using assumption parent module %s for parent class %s!' % (parentModule, parentClass)
                    parentClasses.append(parentClass)
                else:
                    continue

            else:
                parentClasses.append(parentClass)
                parentModule = IMPORTS.get(parentClass, self.dclass2module.get(parentClass))

            file += 'from ' + parentModule + '.' + parentClass + ' import ' + parentClass + '\n'

        file += '\n'
        file += 'class %s%s:\n' % (className, self.formatParentClasses(parentClasses))
        file += INDENT + 'pass\n'

        f.write(file)
        f.close()

    def formatParentClasses(self, parentClasses):
        if len(parentClasses) == 1:
            return '(%s)' % parentClasses[0]
        return str(tuple(parentClasses)).replace('\'', '')

    def removeDelimiter(self, className):
        return className[:-2]

    def generateField(self, dcField, className):
        fileName = self.dclass2module[className].replace('.', '/') + '/' + className
        if dcField.isAirecv():
            for classdel in ('AI', 'UD'):
                if className + classdel in self.dclass2module.keys():
                    self.writeField(fileName, dcField, classDelimiter=classdel)
                    print 'Wrote in %s' % (className + classdel)
        elif dcField.isBroadcast() and not dcField.isClsend():
            for classdel in ('AI', 'UD'):
                if className + classdel in self.dclass2module.keys():
                    self.writeField(fileName, dcField, classDelimiter=classdel)
                    print 'Wrote in %s' % (className + classdel)
        elif dcField.isOwnrecv():
            for classdel in ('AI', 'UD'):
                if className + classdel in self.dclass2module.keys():
                    self.writeField(fileName, dcField, classDelimiter=classdel)
                    print 'Wrote in %s' % (className + classdel)
        elif dcField.isClsend():
            self.writeField(fileName, dcField)
            print 'Wrote in base class %s' % className
        else:
            for classdel in ('', 'AI', 'UD'):
                if className + classdel in self.dclass2module.keys():
                    self.writeField(fileName, dcField, classDelimiter=classdel)
                    print 'Wrote in %s' % (className + classdel)

    def writeField(self, fileName, dcField, classDelimiter=''):
            f = open(
                fileName + classDelimiter + '.py', 'r+'
            )
            newFile = False
            lines = f.readlines()
            for line in lines:
                if 'pass' in line:
                    newFile = True
            if newFile:
                del lines[-1]
            elif lines[-1] != '\n':
                lines.append('\n')
            numargs = len(self.getParameterList(dcField))
            if not numargs:
                f.close()
                return
            lines.append(INDENT + 'def %s%s:\n' % (dcField.getName(), self.getTodoString(numargs)))
            lines.append(INDENT + INDENT + '#' + str(dcField))
            lines.append(INDENT + INDENT + 'return\n')
            f.seek(0, 0)
            f.writelines(lines)
            f.close()

    def getParameterList(self, dcField):
        try:
            return str(dcField).split(dcField.getName() + '(')[1].split(')')[0].split(',')
        except:
            return ''

    def getTodoString(self, n):
        if n == 1:
            return '(todo0)'
        s = []
        for i in xrange(n):
            s.append('todo%d' % i)
        return str(tuple(s)).replace('\'', '')

DCStubGenerator('test.dc')
