# -*- coding: utf-8 -*-

import re
import os
import sys
import codecs
import string

from wb import *
import grt
import mforms


"""
Classe permettant de manipuler le schema de la base de données
"""
class Schema:
    def __init__(self, schema, basepath, namespace):
        self.schema = schema
        self.tables = schema.tables
        self.basepath = basepath
        self.namespace = namespace
        self.dico_table = {}
        self._initDico()

    def _initDico(self):
        for table in self.tables:
            self.dico_table[table.name] = Table(table, self.namespace)
        for table in self.dico_table.values():
            for key in table.getForeignsKey().values():
                if key.many_to_one:
                    self.dico_table[key.origin_table].addInverted(key)

    def processing(self):
        try:
            for table in self.dico_table.values():
                content = self.buildClass(table)
                self.write(content, table)
            return True
        except:
            mforms.Utilities.show_error("", "Unexpected error : " + sys.exc_info()[0], "OK", "", "")
            return False

    """
    Ecrit le contenu de la classe dans un fichier
    """
    def write(self, content, table):
        if not os.path.isdir(self.basepath):
            os.makedirs(self.basepath)

        filename = os.path.join(self.basepath, underscoreToCamelcase(table.name) + ".php")
        file = codecs.open(filename, "w", "utf-8")
        file.write(content)
        file.close()

    """
    Contruction de la classe pour la table passée en argument
    """
    def buildClass(self, table):
        def convertStr(data):
            if isinstance(data, str):
                return unicode(data, "utf-8")
            return data

        content = ""
        properties = ""
        content_key = ""
        constructor = ""
        getters = ""
        setters = ""
        to_string = ""

        content += self.buildHeader(table)

        for column in table.getColumns():
            properties += convertStr(self.buildProperties(column))
            getters += self.buildGetter(column)
            setters += self.buildSetter(column)
            to_string += column.getToString()
            if column.hasDefaultValue():
                constructor += column.getConstructor()

        for key in table.getInvertedKeys():
            content_key += key.buildAnnotations()
            content_key += key.buildProperty()
            constructor += key.buildConstructor()
            setters     += key.buildSetter()
            setters     += key.buildAdder()
            setters     += key.buildRemover()
            getters     += key.buildGetter()

        if constructor != "":
            content_constructor = constructor
            constructor  = Comment(["Constructor of the " + underscoreToCamelcase(table.name) + " class"]).build()
            constructor += "    public function __construct()\n"
            constructor += "    {\n"
            constructor += "{0}".format(content_constructor)
            constructor += "    }\n\n"

        content += convertStr(properties) + convertStr(content_key) + convertStr(constructor)
        content += convertStr(to_string) + convertStr(getters) + convertStr(setters)

        if table.hasTimestamps == True:
            content += convertStr(self.buildTimestamps(table))

        content = content.strip(string.whitespace)

        content += convertStr(self.buildFooter(table))

        return content.strip(string.whitespace)

    """
    Contruction du header de la classe pour la table passée en argument
    """
    def buildHeader(self, table):
        content = "<?php\n\n"
        content += "namespace {0};\n\n".format(self.namespace)
        content += "use Doctrine\ORM\Mapping as ORM;\n"
        content += "use Symfony\Component\Validator\Constraints as Assert;\n"
        if table.hasInvertedKeys():
            content += "use Doctrine\Common\Collections\ArrayCollection;\n"
            for inverted_key in table.getInvertedKeys():
                content += inverted_key.getUse()
        content += "\n"

        header_comment = [
            underscoreToCamelcase(table.name),
            "",
            a_.get("Table", {
                "name": table.name,
                "indexes": [index.toAnnotation("Index") for index in table.getIndexes() if index.isIndex()],
                "uniqueConstraints": [index.toAnnotation("UniqueConstraint") for index in table.getIndexes() if index.isUnique()],
            }),
            a_.get("Entity")
        ]

        if table.hasTimestamps == True:
            header_comment += [a_.get("HasLifecycleCallbacks")]

        commentary = Comment(header_comment, "")

        content += commentary.build()
        content +=  "class {0}\n".format(underscoreToCamelcase(table.name))
        content +=  "{\n"

        return content

    """
    Contruction du footer de la classe pour la table passée en argument
    """
    def buildFooter(self, table):
        return "\n}"

    """
    Contruction de la variable pour la colonne passée en argument
    """
    def buildProperties(self, column):
        return column.getAnnotations() + column.getProperty() + "\n"


    """
    Contruction du getter pour la colonne passée en argument
    """
    def buildGetter(self, column):
        return column.getGetter() + "\n"

    """
    Contruction du setter pour la colonne passée en argument
    """
    def buildSetter(self, column):
        return column.getSetter() + "\n"

    def buildTimestamps(self, table):
        timestamps  = Comment([a_.get("PrePersist"), a_.get("PreUpdate")]).build()
        timestamps += "    public function updatedTimestamps()\n"
        timestamps += "    {\n"
        timestamps += "        $this->setUpdatedAt(new \DateTime());\n"
        timestamps += "        if ($this->getCreatedAt() === null) {\n"
        timestamps += "            $this->setCreatedAt(new \DateTime());\n"
        timestamps += "        }\n"
        timestamps += "    }\n\n"
        return timestamps


class ForeignKey:
    def __init__(self, foreign_key, namespace):
        self.foreign_key = foreign_key
        self.namespace = namespace
        self.name = foreign_key.columns[0].name
        self.many_to_one = (foreign_key.many == 1)
        self.columns = [column.name for column in foreign_key.columns]
        self.table = foreign_key.columns[0].owner.name
        self.origin_table = foreign_key.referencedTable.name
        self.origin_columns = [column.name for column in foreign_key.referencedColumns]
        self.type = ''
        self.setType()

    def getLocals(self):
        return self.columns

    def getForeigns(self):
        return [{'table': self.origin_table, 'column': column} for column in self.origin_columns]

    def isManyToOne(self):
        return self.many_to_one

    def getName(self):
        return self.name

    def setType(self):
        ref_columns = len(self.foreign_key.referencedColumns)
        if self.foreign_key.many == 1:
            if ref_columns > 1:
                self.type = 'ManyToMany'
            else:
                self.type = 'ManyToOne'
        elif ref_columns > 1:
            self.type = 'OneToMany'
        else:
            self.type = 'OneToOne'

    def buildAnnotation(self):
        annotations = []
        annotations += [a_.get(self.type, {'targetEntity': self.namespace + '\\' + underscoreToCamelcase(self.origin_table), 'inversedBy': toPlural(self.table)})]
        annotations += [a_.get('JoinColumn', {'name': self.columns[0], 'referencedColumnName': self.origin_columns[0]})]
        return annotations


class Table:
    def __init__(self, table, namespace):
        self.table = table
        self.name = table.name
        self.namespace = namespace
        self.columns = []
        self.indexes = []
        self.primaries = []
        self.uniques = []
        self.inverted = []
        self.foreigns = {}
        self.hasTimestamps = False
        self._initForeigns()
        self._initIndexes()
        self._initColumns()

    def _initIndexes(self):
        for index in self.table.indices:
            idx = Index(index)
            if idx.isPrimary():
                self.primaries += idx.getColumns()
            elif idx.isUnique():
                self.uniques += idx.getColumns()
            self.indexes += [idx]

    def _initColumns(self):
        for column in self.table.columns:
            col = Column(column)
            if column.name in self.primaries:
                col.markAsPrimary()
            if column.name in self.uniques:
                col.markAsUnique()
            if column.name in self.foreigns:
                col.markAsForeign(self.foreigns[column.name])
            if column.name == 'created_at' or column.name == 'updated_at':
                self.hasTimestamps = True
            self.columns += [col]

    def _initForeigns(self):
        for key in self.table.foreignKeys:
            fks = ForeignKey(key, self.namespace)
            self.foreigns[key.columns[0].name] = fks

    def getColumns(self):
        return self.columns

    def getIndexes(self):
        return self.indexes

    def addInverted(self, key):
        if key.many_to_one:
            self.inverted.append(InvertedKey(key))

    def getForeignsKey(self):
        return self.foreigns

    def getInvertedKeys(self):
        return self.inverted

    def hasInvertedKeys(self):
        return len(self.inverted) > 0


class Index:
    def __init__(self, index):
        self.index = index
        self.name = index.name
        self.type = index.indexType

    def isPrimary(self):
        return self.type == "PRIMARY"

    def isUnique(self):
        return self.type == "UNIQUE"

    def isIndex(self):
        return self.type == "INDEX"

    def getColumns(self):
        return [column.referencedColumn.name for column in self.index.columns]

    def toAnnotation(self, annotation):
        return a_.get(annotation, {
            "name": self.name,
            "columns": self.getColumns()
        })


class InvertedKey:
    def __init__(self, key):
        self.foreign = key
        self.property = ""

    def buildAnnotations(self):
        annotations = ["@var ArrayCollection"]
        annotations += [a_.get('OneToMany', {'targetEntity': self.foreign.namespace + '\\' + underscoreToCamelcase(self.foreign.table), 'mappedBy': self.foreign.origin_table + ''})]
        commentary = Comment(annotations)
        return commentary.build()

    def buildSetter(self):
        annotations = ["Set the value of " + self.property, "@param  ArrayCollection     $" + self.property, "@return self"]
        commentary = Comment(annotations)
        setter = commentary.build()
        setter += "    public function set" + underscoreToCamelcase(self.property) + "(ArrayCollection $" + self.property + ")\n"
        setter += "    {\n"
        setter += "        $this->" + self.property + " = $" + self.property + ";\n"
        setter += "        return $this;\n"
        setter += "    }\n\n\n"
        return setter

    def buildAdder(self):
        table = self.foreign.table
        annotations = ["Add a " + underscoreToCamelcase(table) + " into " + underscoreToCamelcase(self.foreign.origin_table), "@param  " + underscoreToCamelcase(table) + "     $" + table, "@return self"]
        commentary = Comment(annotations)
        adder = commentary.build()
        adder += "    public function add" + underscoreToCamelcase(table) + "(" + underscoreToCamelcase(table) + " $" + table + ")\n"
        adder += "    {\n"
        adder += "        if ($this->" + self.property + "->contains($" + table + ") === false) {\n"
        adder += "            $this->" + self.property + "->add($" + table + ");\n"
        adder += "            $" + table + "->set" + underscoreToCamelcase(self.foreign.origin_table) + "($this);\n"
        adder += "        }\n"
        adder += "        return $this;\n"
        adder += "    }\n\n\n"
        return adder

    def buildRemover(self):
        table = self.foreign.table
        annotations = ["Remove a " + underscoreToCamelcase(table) + " into " + underscoreToCamelcase(self.foreign.origin_table), "@param  " + underscoreToCamelcase(table) + "     $" + table, "@return self"]
        commentary = Comment(annotations)
        adder = commentary.build()
        adder += "    public function remove" + underscoreToCamelcase(table) + "(" + underscoreToCamelcase(table) + " $" + table + ")\n"
        adder += "    {\n"
        adder += "        if ($this->" + self.property + "->contains($" + table + ") === true) {\n"
        adder += "            $this->" + self.property + "->remove($" + table + ");\n"
        adder += "            $" + table + "->set" + underscoreToCamelcase(self.foreign.origin_table) + "(null);\n"
        adder += "        }\n"
        adder += "        return $this;\n"
        adder += "    }\n\n\n"
        return adder

    def buildGetter(self):
        commentary = Comment(["Get the value of " + self.property, "@return " + underscoreToCamelcase(self.property) + "[]"])
        getter = commentary.build()
        getter += "    public function get" + underscoreToCamelcase(self.property) + "()\n"
        getter += "    {\n"
        getter += "        return $this->" + self.property + ";\n"
        getter += "    }\n\n\n"
        return getter

    def getUse(self):
        return "use " + self.foreign.namespace + '\\' + underscoreToCamelcase(self.foreign.table) + ";\n";

    def buildProperty(self):
        self.property = toPlural(self.foreign.table)
        return "    protected $" + self.property + ";\n\n"

    def buildConstructor(self):
        return "        $this->" + self.property + " = new ArrayCollection();\n"


class Column:
    def __init__(self, column):
        self.column = column
        self.name = column.name
        self.type = column.simpleType if column.simpleType else column.userType
        self.flags = column.flags
        self.is_primary = False
        self.is_unique = False
        self.is_foreign = False
        self.foreign_key = None
        self.doctrine_types = {
            "TINYINT": "integer",
            "SMALLINT": "integer",
            "MEDIUMINT": "integer",
            "INT": "integer",
            "BIGINT": "integer",
            "FLOAT": "float",
            "DOUBLE": "float",
            "float": "float",
            "CHAR": "string",
            "VARCHAR": "string",
            "BINARY": "string",
            "VARBINARY": "string",
            "TINYTEXT": "string",
            "TEXT": "string",
            "MEDIUMTEXT": "string",
            "LONGTEXT": "string",
            "TINYBLOB": "string",
            "BLOB": "string",
            "MEDIUMBLOB": "string",
            "LONGBLOB": "string",
            "DATETIME": "datetime",
            "DATE": "datetime",
            "TIME": "datetime",
            "YEAR": "integer",
            "TIMESTAMP": "datetime",
            "GEOMETRY": "object",
            "LINESTRING": "object",
            "POLYGON": "object",
            "MULTIPOINT": "object",
            "MULTILINESTRING": "object",
            "MULTIPOLYGON": "object",
            "GEOMETRYCOLLECTION": "object",
            "BIT": "integer",
            "ENUM": "string",
            "SET": "string",
            "BOOLEAN": "boolean",
            "BOOL": "boolean",
            "FIXED": "float",
            "FLOAT4": "float",
            "FLOAT8": "float",
            "INT1": "integer",
            "INT2": "integer",
            "INT3": "integer",
            "INT4": "integer",
            "INT8": "integer",
            "INTEGER": "integer",
            "LONGVARBINARY": "string",
            "LONGVARCHAR": "string",
            "LONG": "integer",
            "MIDDLEINT": "integer",
            "NUMERIC": "float",
            "DEC": "float",
            "CHARACTER": "string"
        }
        self.php_types = {
            "TINYINT": "int",
            "SMALLINT": "int",
            "MEDIUMINT": "int",
            "INT": "int",
            "BIGINT": "int",
            "FLOAT": "float",
            "DOUBLE": "float",
            "float": "float",
            "CHAR": "string",
            "VARCHAR": "string",
            "BINARY": "string",
            "VARBINARY": "string",
            "TINYTEXT": "string",
            "TEXT": "string",
            "MEDIUMTEXT": "string",
            "LONGTEXT": "string",
            "TINYBLOB": "string",
            "BLOB": "string",
            "MEDIUMBLOB": "string",
            "LONGBLOB": "string",
            "DATETIME": "\DateTime",
            "DATE": "\DateTime",
            "TIME": "\DateTime",
            "YEAR": "int",
            "TIMESTAMP": "\DateTime",
            "GEOMETRY": "object",
            "LINESTRING": "object",
            "POLYGON": "object",
            "MULTIPOINT": "object",
            "MULTILINESTRING": "object",
            "MULTIPOLYGON": "object",
            "GEOMETRYCOLLECTION": "object",
            "BIT": "int",
            "ENUM": "string",
            "SET": "string",
            "BOOLEAN": "bool",
            "BOOL": "bool",
            "FIXED": "float",
            "FLOAT4": "float",
            "FLOAT8": "float",
            "INT1": "int",
            "INT2": "int",
            "INT3": "int",
            "INT4": "int",
            "INT8": "int",
            "INTEGER": "int",
            "LONGVARBINARY": "string",
            "LONGVARCHAR": "string",
            "LONG": "int",
            "MIDDLEINT": "int",
            "NUMERIC": "float",
            "DEC": "float",
            "CHARACTER": "string"
        }

    def _getDoctrineType(self):
        return self.doctrine_types.get(self.type.name, "string")

    def _getPhpType(self):
        if self.is_foreign == False:
            return self.php_types.get(self.type.name, "string")
        return underscoreToCamelcase(self.foreign_key.origin_table)

    def _isUnsigned(self):
        return "UNSIGNED" in self.column.flags

    def _isAutoIncrement(self):
        return self.column.autoIncrement == 1

    def _isNotNull(self):
        return self.column.isNotNull == 1

    def _getLength(self):
        return self.column.length if self.column.length != -1 else None

    def _getPrecision(self):
        return self.column.precision if self.column.precision != -1 else None

    def _getParameters(self):
        return self.column.datatypeExplicitParams if self.column.datatypeExplicitParams else None

    def _getFinalName(self):
        if self.is_foreign:
            # Remove "_id"
            long = len(self.name) - 3
            final_name = self.name[0:long]
        else:
            final_name = self.name
        return final_name

    def markAsPrimary(self):
        self.is_primary = True

    def markAsUnique(self):
        self.is_unique = True

    def markAsForeign(self, foreign_key):
        self.is_foreign = True
        self.foreign_key = foreign_key

    def hasDefaultValue(self):
        if self.column.defaultValueIsNull == 1:
            return True
        if self.column.defaultValue != "":
            return True
        return False

    def getDefaultValue(self):
        if self.column.defaultValueIsNull == 1:
            return "null"
        if self._getPhpType() == "bool":
            if self.column.defaultValue == "1":
                return "true"
            else:
                return "false"
        if self._getPhpType() == "string":
            default_value = self.column.defaultValue
            default_value = re.sub("^'", "", default_value)
            default_value = re.sub("'$", "", default_value)
            default_value = default_value.replace("'", "\\'")
            return "'" + default_value + "'"
        if self._getPhpType() == "\DateTime":
            return "new \DateTime(\"" + self.column.defaultValue + "\")"
        return self.column.defaultValue

    def getConstructor(self):
        return "        $this->" + self._getFinalName() + " = " + self.getDefaultValue() + ";\n"

    def getAnnotations(self):
        annotations = []

        if self.column.comment != "":
            annotations += [self.column.comment]
            annotations += [""]

        annotations += ["@var " + self._getPhpType()]

        if self.is_primary:
            annotations += [a_.get("Id")]
        def_column = {"type": self._getDoctrineType()}
        if self._getLength():
            def_column["length"] = int(self._getLength())
        if not self._isNotNull():
            def_column["nullable"] = True
        if self.is_unique:
            def_column["unique"] = True
        if self._getPrecision():
            def_column["precision"] = self._getPrecision()
        if self._isUnsigned():
            def_column["options"] = {"\"unsigned\"": True}

        annotations += [a_.get("Column", def_column)]

        if self._isAutoIncrement():
            annotations += [a_.get("GeneratedValue", {"strategy": "AUTO"})]

        annotations += self.getAssertAnnotation()

        if self.is_foreign:
            annotations = self.foreign_key.buildAnnotation()

        commentary = Comment(annotations)
        return commentary.build()

    def getAssertAnnotation(self):
        annotations = []

        if self.is_primary:
            return annotations

        a_.setPrefix("@Assert\\")

        if self._getLength():
            annotations += [a_.get("Length", {"min": 0, "max": self._getLength()})]
        if self._isNotNull() and self._getPhpType() != "string":
            annotations += [a_.get("NotNull", {})]
        if self._isNotNull() and self._getPhpType() == "string":
            annotations += [a_.get("NotBlank", {})]
        if self._isUnsigned():
            annotations += [a_.get("GreaterThanOrEqual", {"value": 0})]
        if self.name == "email":
            annotations += [a_.get("Email", {})]
        if self._getPhpType() == "int" or self._getPhpType() == "float":
            annotations += [a_.get("Type", {"type": "numeric"})]
        if self._getPhpType() == "string":
            annotations += [a_.get("Type", {"type": "string"})]
        if self._getPhpType() == "\DateTime":
            annotations += [a_.get("DateTime", {})]

        a_.resetPrefix()
        return annotations

    def getProperty(self):
        return "    protected $" + self._getFinalName() + ";\n"

    def getGetter(self):
        commentary = Comment(["Get the value of " + self._getFinalName(), "@return " + self._getPhpType()])
        result = commentary.build()
        result += "    public function get" + underscoreToCamelcase(self._getFinalName()) + "()\n"
        result += "    {\n"
        result += "        return $this->" + self._getFinalName() + ";\n"
        result += "    }\n\n"
        return result

    def getSetter(self):
        commentary = Comment(["Set the value of " + self._getFinalName(), "@param " + self._getPhpType() + " $" + self._getFinalName(), "@return self"])
        result = commentary.build()
        result += "    public function set" + underscoreToCamelcase(self._getFinalName()) + "($" + self._getFinalName() + ")\n"
        result += "    {\n"
        result += "        $this->" + self._getFinalName() + " = $" + self._getFinalName() + ";\n"
        result += "        return $this;\n"
        result += "    }\n\n"
        return result

    def getToString(self):
        if self.name != 'name':
            return ''

        commentary = Comment(['Return the name when show the object', '@return string'])
        result = commentary.build()
        result += "    public function __toString()\n"
        result += "    {\n"
        result += "        return $this->getName() ?: '-';\n"
        result += "    }\n\n"

        return result


"""
Classe permettant de générer des annotations
"""
class Annotation:
    def __init__(self):
        self._default_prefix = "@ORM\\"
        self.prefix = self._default_prefix

    def setPrefix(self, prefix):
        self.prefix = prefix

    def resetPrefix(self):
        self.prefix = self._default_prefix

    def get(self, name, value = None):
        def buildDict(datas):
            def quoted(value):
                if isinstance(value, bool):
                    return "true" if value else "false"
                elif isinstance(value, basestring) and value[0:len(self.prefix)] != self.prefix:
                    return '"' + value + '"'
                elif isinstance(value, dict):
                    return "{" + buildDict(value) + "}"
                elif isinstance(value, list):
                    return "{" + ", ".join([quoted(val) for val in value]) + "}"
                else:
                    return str(value)

            return ", ".join([key + '=' + quoted(value) for key, value in datas.iteritems()])

        annotation = self.prefix + name

        if isinstance(value, dict):
            annotation += "(" + buildDict(value) + ")"

        return annotation


"""
Classe permettant de générer des commentaires
"""
class Comment:
    def __init__(self, comments, prefix = "    "):
        self.comments = comments
        self.prefix = prefix
        self.eol = "\n"

    def build(self):
        result = self.get("/**", False)
        for comment in self.comments:
            result += self.get(comment)
        result += self.get(" */", False)
        return result

    def get(self, text, content = True):
        return self.prefix + (" * " if content else "") + text + self.eol


"""
Modification d'une chaine avec underscore en CamelCase

:param:     string  value   La chaine à convertir
:return:    string          La chaine au format CamelCase
"""
def underscoreToCamelcase(value):
    def camelcase(): 
        yield str.lower
        while True:
            yield str.capitalize

    c = camelcase()
    result = "".join(c.next()(x) if x else '_' for x in value.split("_"))
    return result[0].upper() + result[1:]

"""
Retourne une chaine convertie au pluriel

:param:     string  value   La chaine au singulier
:return:    string          La chaine au pluriel
"""
def toPlural(value):
    if value[-1] != "y":
        return value + "s"

    return value[0:-1] + "ies"


#################################################
#
# Main
#
#################################################
a_ = Annotation()


ModuleInfo = DefineModule(name="Doctrine Annotation", author="Simon Leblanc", version="1.0", description="Contains Plugin Doctrine")


# This plugin takes no arguments
@ModuleInfo.plugin("Doctrine", 
                    caption="Build Doctrine Entities", 
                    description="The plugin allow you to generate Doctrine Entities class from your schema",
                    input=[wbinputs.currentCatalog()], 
                    pluginMenu="Utilities"
)
@ModuleInfo.export(grt.INT, grt.classes.db_Catalog)
def Doctrine(catalog):
    ret, namespace = mforms.Utilities.request_input("Namespace", "Set the namespace to use in the entities", "AppBundle\Entity")
    if not ret:
        return 0

    basepath = os.path.expanduser(os.path.join("~", "mysql-workbench", catalog.schemata[0].name))
    schema = Schema(catalog.schemata[0], basepath, namespace)
    
    if not schema.processing():
        mforms.Utilities.show_error("Build Doctrine Entities", "Your entities has not build :(", "OK", "", "")

    mforms.Utilities.show_message("Build Doctrine Entities", "Your entities has been build in {0}".format(basepath), "OK", "", "")
    return 0
