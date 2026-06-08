# Brightspace MCP — Quick Reference Prompts

Copy-paste any of these into Claude Code chat.

## Me / Auth
```
who am I in Brightspace?
list the Brightspace API versions supported by this instance
```

## Users
```
find the Brightspace user with username "jsmith"
find the Brightspace user with email "teacher@school.org"
get Brightspace user 183
```

## Org Structure
```
get the Brightspace organization info
list all org unit types in Brightspace
search Brightspace org units of type "Course Offering" named "Math"
search Brightspace for all course offerings and summarize what you find
get the descendants of Brightspace org unit 6606
```

## Enrollments
```
list all enrollments for Brightspace user 183
get the classlist for Brightspace org unit 12345
list all users enrolled in org unit 12345
```

## Grades
```
list all grade items in Brightspace course 12345
get all grades for user 183 in course 12345
get the final grade for user 183 in course 12345
```

## Data Hub
```
list all available Brightspace Data Sets
list the advanced data sets available in Brightspace
```

## Raw API (explore any endpoint from the Valence docs)
```
do a raw Brightspace API GET on "/lp/1.60/users/whoami"
do a raw Brightspace GET on "/lp/1.60/organization/info"
```

## Multi-step (let Claude chain the tools)
```
find the course offering named "Algebra I", get its classlist, and summarize enrollment
find user "jsmith" and list all their course enrollments
get the org structure and describe how the institution is organized
list all Brightspace Data Sets and tell me which ones would be useful for attendance reporting
```
