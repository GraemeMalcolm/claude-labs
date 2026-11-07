---
layout: default
title: Claude Labs
---

# Claude Labs

Select a lab to view its instructions.

{% assign labs = site.pages | where_exp: "doc", "doc.path contains 'Instructions/'" | sort: "path" %}
<ul class="lab-list">
{% for doc in labs %}
  <li>
    <a href="{{ doc.url | remove_first: '/' }}">{{ doc.lab.title | default: doc.name }}</a>
    {% if doc.lab.description %}<p>{{ doc.lab.description }}</p>{% endif %}
  </li>
{% endfor %}
</ul>
