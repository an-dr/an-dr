# pag

The main aim of this package is to satisfy some routing requirements in working with files and strings.

A **path** class was implemented to:
 * recognize a type of path, using different features like prefix (file://, svn://) and variants of writing, f.ex. /, \\, \ slashes and others
 * operation with a path (including overloaded operators)
 * transform any kind of paths in unified string form
 * recognize a file extension
 
 **Timermult** class is using to generate a thread with timers, which is works indifferent of the main thread. Communication is realized through standard list class, which is declared in outer thread and changes by a timermult object

Class conv has a lot of static methods to:
* Convert str<->int
* Recognize type number system in conversion using '0x', '0b' and other features at writing as string 
* Print numbers in needed form, f.ex. 16-> 0x0010;  

## Installing
The package is provided without any installers. Maybe a bit later I'll make a standard archive for pip

## Classes
