---
layout: default
title: Claude Labs
---

# Claude Labs

<img class="banner" src="assets/banner.svg" alt="Hand-drawn sketch of a programmer working at a computer.">

{% include labs-overview.md %}

> **Tip**: Each lab page includes an **Ask Claude** button that opens a chat assistant to help you with the lab. To use it, you need your own Claude API key (from the Claude Console). The key is stored only in your browser tab and is cleared when you close the tab, and usage is billed to your Console account.

{% assign labs = site.pages | where_exp: "doc", "doc.path contains 'Instructions/'" | sort: "path" %}
<ul class="lab-list">
{% for doc in labs %}
  <li>
    <a href="{{ doc.url | remove_first: '/' }}">{{ doc.lab.title | default: doc.name }}</a>
    {% if doc.lab.description %}<p>{{ doc.lab.description }}</p>{% endif %}
  </li>
{% endfor %}
</ul>
