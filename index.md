---
layout: default
title: Claude Labs
---

# Claude Labs

{% include labs-overview.md %}

Select a lab to view its instructions. Start with the first lab.

{% assign labs = site.pages | where_exp: "doc", "doc.path contains 'Instructions/'" | sort: "path" %}
<ul class="lab-list">
{% for doc in labs %}
  <li>
    <a href="{{ doc.url | remove_first: '/' }}">{{ doc.lab.title | default: doc.name }}</a>
    {% if doc.lab.description %}<p>{{ doc.lab.description }}</p>{% endif %}
  </li>
{% endfor %}
</ul>
