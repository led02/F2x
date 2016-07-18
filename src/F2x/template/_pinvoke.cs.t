/* This file was generated by F2x. Please do not change directly! */
using System;
using System.Runtime.InteropServices;
{%- for typ in module.types %}

class {{ typ.name }} {
	internal IntPtr c_ptr;
	private Boolean is_ref;
	
	public {{ typ.name }}() {
		this.c_ptr = {{ typ.name }}_new();
		this.is_ref = false;
	}
	
	internal {{ typ.name }}(IntPtr c_ptr) {
		this.c_ptr = c_ptr;
		this.is_ref = false;
	}
	
	internal {{ typ.name }}(IntPtr c_ptr, Boolean is_ref) {
		this.c_ptr = c_ptr;
		this.is_ref = is_ref;
	}
	
	~{{ typ.name }}() {
		if (!this.is_ref) {
			{{ typ.name }}_free(this.c_ptr);
		}
	}
	
	[DllImport("{{ config.get('generate', 'dll') }}", EntryPoint="{{ typ.name }}_new")]
	private extern static IntPtr {{ typ.name }}_new();
	[DllImport("{{ config.get('generate', 'dll') }}", EntryPoint="{{ typ.name }}_free")]
	private extern static void {{ typ.name }}_free(IntPtr c_ptr);
{%- for field in typ.fields %}

	public {{ field.cstype }} {{ field.name }} {
		get {
	{%- if field.getter == 'function' %}
		{%- if field.ftype %}
			return new {{ field.ftype }}({{ typ.name }}_get_{{ field.name }}(this.c_ptr));
		{%- else %}
			return {{ typ.name }}_get_{{ field.name }}(this.c_ptr);
		{%- endif %}
	{%- elif field.getter == 'subroutine' %}
		{%- if field.strlen %}
			StringBuilder {{ field.name }}_value = new StringBuilder({{ field.strlen }});
	 	{%- elif field.dims %}
			{{ field.name }}_value = new {{ field.cstype }}[{{ ', '.join(field.dims) }}];
		{%- else %}
			{{ field.name }}_value = new {{ field.cstype }}();
		{%- endif %}
			{{ typ.name }}_get_{{ field.name }}(this.c_ptr, {{ field.name }}_value);
			return {{ field.name }}_value;
	{%- endif %}
		}
	{%- if field.setter %}
		set {
			{{ typ.name }}_set_{{ field.name }}(this.c_ptr, value);
		}
	{%- endif %}
	}
	{%- if field.getter == 'function' %}
	[DllImport("{{ config.get('generate', 'dll') }}", EntryPoint="{{ typ.name }}_get_{{ field.name }}")]
	private extern static {{ field.cstype }} {{ typ.name }}_get_{{ field.name }}(IntPtr c_ptr);
	{%- else %}
	[DllImport("{{ config.get('generate', 'dll') }}", EntryPoint="{{ typ.name }}_get_{{ field.name }}")]
	private extern static void {{ typ.name }}_get_{{ field.name }}(IntPtr c_ptr, ref {{ field.cstype }} {{ field.name }}_value);
	{%- endif %}
	{%- if field.setter %}
	[DllImport("{{ config.get('generate', 'dll') }}", EntryPoint="{{ typ.name }}_set_{{ field.name }}")]
	private extern static void {{ typ.name }}_set_{{ field.name }}(IntPtr c_ptr, {{ field.cstype }} {{ field.name }}_value);
	{%- endif %}
{%- endfor %}
}
{%- endfor %}
{%- if config.has_section('export') %}

class {{ module.name }} {
{%- set exports = config.options('export') %}
{%- for function in module.functions %}
{%- if function.name.lower() in exports %}
{%- set export_name = config.get('export', function.name.lower()) %}
{%- set call_args = [] %}
{%- if function.ret.getter == 'function' %}

	[DllImport("{{ config.get('generate', 'dll') }}", EntryPoint="{{ export_name }}")]
	private static extern {% if function.ret.ftype %}IntPtr{% else %}{{ function.ret.cstype }}{% endif %} {{ export_name }}({% for arg in function.args %}{% if arg.dims %}{{ arg.cstype }}[{{ ', '.join(arg.dims) }}]{% elif arg.ftype %}IntPtr{% else %}{{ arg.cstype }}{% endif %} {{ arg.name }}{% if not loop.last %}, {% endif %}{% endfor %});
{%- else %}

	[DllImport("{{ config.get('generate', 'dll') }}", EntryPoint="{{ export_name }}")]
	private static extern void {{ export_name }}({% for arg in function.args %}{% if arg.dims %}{{ arg.cstype }}[{{ ', '.join(arg.dims) }}]{% elif arg.ftype %}IntPtr{% else %}{{ arg.cstype }}{% endif %} {{ arg.name }}, {% endfor %}ref {% if function.ret.ftype %}IntPtr{% elif function.ret.strlen %}StringBuilder{% elif function.ret.dims %}{{ function.ret.cstype }}[{{ ', '.join(function.ret.dims) }}]{% endif %} {{ field.name }}_value);
{%- endif %}
	public static {{ function.ret.cstype }} {{ function.name }}({% for arg in function.args %}{% if arg.dims %}{{ arg.cstype }}[{{ ', '.join(arg.dims) }}]{% else %}{{ arg.cstype }}{% endif %} {{ arg.name }}{% if not loop.last %}, {% endif %}{% endfor %}) {
{%- for arg in function.args %}
	{%- if arg.ftype %}
		{%- do call_args.append(arg.name + '.c_ptr') %}
	{%- else %}
		{%- do call_args.append(arg.name) %}
	{%- endif %}
{%- endfor %}
{%- if function.ret.getter == 'function' %}
	{%- if function.ret.ftype %}
		return new {{ function.ret.ftype }}({{ export_name }}({{ ', '.join(call_args) }}), false);
	{%- else %}
		return {{ export_name }}({{ ', '.join(call_args) }});
	{%- endif %}
{%- elif function.ret.getter == 'subroutine' %}
	{%- if function.ret.strlen %}
		{{ export_name }}_value = new StringBuilder({{ function.ret.strlen }});
		{%- do call_args.append(export_name + '_value') %}
	{%- endif %}
		{{ export_name}}({{ ', '.join(call_args) }});
		return {{ export_name }}_value;
{%- endif %}
	}
{%- endif %}
{%- endfor %}
{%- for subroutine in module.subroutine %}
{%- if subroutine.name.lower() in exports %}
{%- set export_name = config.get('export', subroutine.name.lower()) %}
{%- set call_args = [] %}

	[DllImport("{{ config.get('generate', 'dll') }}", EntryPoint="{{ export_name }}")]
	private static extern void {{ export_name }}({% for arg in function.args %}{% if arg.dims %}{{ arg.cstype }}[{{ ', '.join(arg.dims) }}]{% elif arg.ftype %}IntPtr{% else %}{{ arg.cstype }}{% endif %} {{ arg.name }}{% if not loop.last %}, {% endif %}{% endfor %});
	public static void {{ subroutine.name }}({% for arg in function.args %}{% if arg.dims %}{{ arg.cstype }}[{{ ', '.join(arg.dims) }}]{% else %}{{ arg.cstype }}{% endif %} {{ arg.name }}{% if not loop.last %}, {% endif %}{% endfor %}) {
{%- for arg in subroutine.args %}
	{%- if arg.ftype %}
		{%- do call_args.append(arg.name + '.c_ptr') %}
	{%- else %}
		{%- do call_args.append(arg.name) %}
	{%- endif %}
{%- endfor %}
		{{ export_name}}({{ ', '.join(call_args) }})
{%- endif %}
{%- endfor %}
}
{%- endif %}

