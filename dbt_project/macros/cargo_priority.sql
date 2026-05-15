
{% macro cargo_priority(column_name) %}
    case
        when {{ column_name }} = 'medical' then 'critical'
        when {{ column_name }} in ('fuel_cells', 'humanitarian_aid') then 'high'
        else 'standard'
    end
{% endmacro %}
