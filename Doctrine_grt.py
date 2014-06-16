# -*- coding: utf-8 -*-

import re
import os
import sys

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

    def processing(self):
        try:
            for table in self.tables:
                tab = Table(table)
                content = self.buildClass(tab)
                self.write(content, tab)

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
        file = open(filename, "w")
        file.write(content)
        file.close()


    """
    Contruction de la classe pour la table passée en argument
    """
    def buildClass(self, table):
        content = ""
        properties = ""
        getters = ""
        setters = ""

        content += self.buildHeader(table)

        for column in table.getColumns():
            properties += self.buildProperties(column)
            getters += self.buildGetter(column)
            setters += self.buildSetter(column)

        content += properties + getters + setters

        content += self.buildFooter(table)

        return content


    """
    Contruction du header de la classe pour la table passée en argument
    """
    def buildHeader(self, table):
        content = "<?php\n\n"
        content += "namespace {0};\n\n".format(self.namespace)
        content += "use Doctrine\ORM\Mapping as ORM;\n"
        content += "use Symfony\Component\Validator\Constraints as Assert;\n\n"

        commentary = Comment([
            underscoreToCamelcase(table.name),
            "",
            a_.get("Table", {
                "name": table.name,
                "indexes": [ index.toAnnotation("Index") for index in table.getIndexes() if index.isIndex() ],
                "uniqueConstraints": [ index.toAnnotation("UniqueConstraint") for index in table.getIndexes() if index.isUnique() ],
            }),
            a_.get("Entity")
        ], "")

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


class Table:
    def __init__(self, table):
        self.table = table
        self.name = table.name
        self.columns = []
        self.indexes = []
        self.primaries = []
        self._initIndexes()
        self._initColumns()

    def _initIndexes(self):
        for index in self.table.indices:
            idx = Index(index)
            if idx.isPrimary():
                self.primaries += idx.getColumns()
            self.indexes += [idx]

    def _initColumns(self):
        for column in self.table.columns:
            col = Column(column)
            if column.name in self.primaries:
                col.markAsPrimary()
            self.columns += [col]

    def getColumns(self):
        return self.columns

    def getIndexes(self):
        return self.indexes



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


class Column:
    def __init__(self, column):
        self.column = column
        self.name = column.name
        self.type = column.simpleType if column.simpleType else column.userType
        self.flags = column.flags
        self.is_primary = False
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
        return self.php_types.get(self.type.name, "string")

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

    def markAsPrimary(self):
        self.is_primary = True

    def getAnnotations(self):
        annotations = []

        if self.is_primary:
            annotations += [a_.get("Id")]

        def_column = {}
        def_column["type"] = self._getDoctrineType()
        if self._getLength():
            def_column["length"] = int(self._getLength())
        if self._isUnsigned():
            def_column["nullable"] = True
        if self._getPrecision():
            def_column["precision"] = self._getPrecision()
        if self._isUnsigned():
            def_column["options"] = {"unsigned": True}

        annotations += [a_.get("Column", def_column)]

        if self._isAutoIncrement():
            annotations += [a_.get("GeneratedValue", {"strategy": "auto"})]

        commentary = Comment(annotations)
        return commentary.build()

    def getProperty(self):
        return "    protected $" + self.name + ";\n"

    def getGetter(self):
        commentary = Comment(["Get the value of " + self.name, "@return " + self._getPhpType()])
        result = commentary.build()
        result += "    public function get" + underscoreToCamelcase(self.name) + "()\n"
        result += "    {\n"
        result += "        return $this->" + self.name + ";\n"
        result += "    }\n\n"

        return result

    def getSetter(self):
        commentary = Comment(["Set the value of " + self.name, "@param " + self._getPhpType() + " $" + self.name, "@return self"])
        result = commentary.build()
        result += "    public function set" + underscoreToCamelcase(self.name) + "($" + self.name + ")\n"
        result += "    {\n"
        result += "        $this->" + self.name + " = $" + self.name + ";\n"
        result += "        return $this;\n"
        result += "    }\n\n"

        return result



"""
Classe permettant de générer des annotations
"""
class Annotation:
    def __init__(self):
        self.prefix = "@ORM\\"


    def get(self, name, value = None):
        def buildDict(datas):
            def quoted(value):
                if isinstance(value, bool):
                    return "true" if value else "false"
                elif isinstance(value, str) and value[0:len(self.prefix)] != self.prefix:
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
    ret, namespace = mforms.Utilities.request_input("Namespace", "Set the namespace to use in the entities", "Portailpro\Bundle\Entity")
    if not ret:
        return 0

    basepath = os.path.expanduser(os.path.join("~", "mysql-workbench", catalog.schemata[0].name))
    schema = Schema(catalog.schemata[0], basepath, namespace)
    
    if not schema.processing():
        mforms.Utilities.show_error("Build Doctrine Entities", "Your entities has not build :(", "OK", "", "")

    mforms.Utilities.show_message("Build Doctrine Entities", "Your entities has been build in {0}".format(basepath), "OK", "", "")
    return 0
