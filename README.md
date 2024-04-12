# pyjsonapi

A JSON:API implementation in Python.

## Usage

```python
from pyjsonapi import Model, ToManyRelationship, Session

class Student(Model, type='student'):
    name: str
    age: int
    classrooms: ToManyRelationship['Classroom']

class Classroom(Model, type='classroom'):
    name: str
    students: ToManyRelationship[Student]

session = Session('http://example.com/api')
student = session.fetch(Student, 'id-of-student')
print(student.name, 'age', student.age)
classrooms = student.classrooms.items
print('classrooms:')
for classroom in classrooms:
    print(classroom.name)
```
