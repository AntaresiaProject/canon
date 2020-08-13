[![Gitpod ready-to-code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/AntaresiaProject/datamapping)

# Expressive Data Mapping
Datamapping exists to allow quick and expressive mapping from one source of data to another. 
It is stand alone and can be used by any project. It is also included in the larger Project forthcoming that 
provides additional tools for larger ETL processes. 



# Features

* Small and Fast - Only a few files and can process well over 500 complex items in a second. 
* Expressive - Create Mappings using Python code, code is easy to understand even for non-programmers
* Scalable - Map Flat File data or Embedded JSON objects



# Getting Started 

Data mapping consists of 2 main objects that can be used.

## SourceMapping
Mappings are expressed as classes that inherit from SourceMapping. Each attribute of a SourceMapping class correlates to 
a key in the source of the data being mapped. 

## FieldMapping
Each attribute in a SourceMapping is set to an instance of FieldMapping. FieldMapping contains all the essential information of 
how that source data maps to the destination data. It can be mapped using a string, A field reference. and a "converter" 
can be expressed to augment the data prior to the mapping.
A few subclasses exist of FieldMapping to provide clearer expression, such as Ignore which can be used to explicitly 
ignore an incoming field. 


## Example
```python
@maps(to=Assessment)
class AssessmentMapping(SourceMapping):
    System_Code = Ignore("This is a tracking code that makes its way to us but we don't want/need it")
    Source_System_Record_Id = FieldMapping(Assessment.id)
    assessment_mode = MapTo("mode")  
    resource_ids = MapTo(Assessment.owner, converter=find_book)

```