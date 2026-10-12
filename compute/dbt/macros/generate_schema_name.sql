{% macro generate_schema_name(custom_schema_name, node) %}
  {# If a custom schema is provided, use it as-is; otherwise fall back to target.schema #}
  {% if custom_schema_name is not none %}
    {{ return(custom_schema_name | trim) }}
  {% else %}
    {{ return(target.schema) }}
  {% endif %}
{% endmacro %}