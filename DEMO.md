# Brightspace Admin MCP — Cheat Sheet

> Ask your LMS in plain English. Claude calls the Brightspace API live — no UI, no tickets.

---

## Pre-flight

Before presenting, run: **"Who am I authenticated as in Brightspace?"**
If it returns your admin profile, you're good. If not, re-auth first.

---

## What You Can Ask Right Now

### Identity & Org
| Ask Claude... | Tool used |
|---|---|
| "Who am I authenticated as?" | `whoami` |
| "What is our Brightspace organization?" | `get_organization` |
| "What types of org units do we have?" | `list_orgunit_types` |
| "Show me everything in our org structure." | `search_orgunits` |
| "What's underneath [org unit]?" | `get_descendants` |

### Users
| Ask Claude... | Tool used |
|---|---|
| "Find the user with email mcreed@mlri.org" | `find_user` |
| "Look up user [id]" | `get_user` |
| "What is [user] enrolled in?" | `list_user_enrollments` |
| "What role does [user] have in [course]?" | `get_user_enrollment` |

### Courses & Enrollments
| Ask Claude... | Tool used |
|---|---|
| "Who is enrolled in [course]?" | `list_orgunit_enrollments` |
| "Pull the classlist with emails for [course]." | `get_classlist` |

### Grades
| Ask Claude... | Tool used |
|---|---|
| "What grade items are in [course]?" | `list_grade_objects` |
| "What are [user]'s grades in [course]?" | `get_user_grades` |
| "What is [user]'s final grade in [course]?" | `get_final_grade` |

### Data Hub
| Ask Claude... | Tool used |
|---|---|
| "What bulk data exports are available?" | `list_brightspace_data_sets` |
| "What advanced analytics exports do we have?" | `list_advanced_data_sets` |
| "Download the [dataset] export." | `download_data_set` |

### Escape Hatch
| Ask Claude... | Tool used |
|---|---|
| "Call [any Brightspace API endpoint] directly." | `api_get` |

---

## Coming Soon — Write Permissions

Once enabled, multi-step admin workflows become a single sentence:

| Today (manual) | With write tools |
|---|---|
| Import student CSV, fix errors, re-upload | "Create accounts for everyone in this list." |
| Navigate to each course, enroll one by one | "Enroll all students in Course X for Fall 2026." |
| Build courses manually in the UI | "Create a course offering for each row here." |
| Export, edit, re-import grade file | "Release final grades for all students in Course X." |
| Submit IT ticket to withdraw a student | "Remove users who withdrew before the add/drop deadline." |

Especially powerful at semester start when standing up courses and loading the student roster.
