{% macro flag_suspicious(column_name) %}
    case
        when voss_flag = 1 or dest_is_federation = false or cargo_type = 'classified'
        then 1
        else 0
    end as {{ column_name }}
{% endmacro %}
