from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
import re
import sys

grammar = Grammar(r"""
	stml_page      = _ doctype (_ tag _)+
	doctype        = ~"<!doctype stml>"i
	tag            = (tag_self / tag_body)
	tag_body       = tag_open _ (tag / tag_self / text)* _ tag_close
	tag_close      = ~"</>"
	tag_open       = ~"<" _ tagname _ (attribute _)* _ ">"
	tag_self       = ~"<" _ tagname _ (attribute _)* _ "/>"
			   
	tagname        = ~"[a-z]+"
	ws             = ~"\\s*"m
	text           = ~"[^<>]+"m
	attribute      = ~"[a-zA-Z]+" "=" ~"[^ />]+"
	_              = ws
""")

class STMLNode:
	"""Defines an STML node."""
	def __init__(self, tag=''):
		self.self_closing = False
		self.tag = tag
		self.children = []
		self.attributes = {}

class TextNode:
	"""Defines a non-STML text body that we actually want to keep. Page text that isn't a TextNode is discarded."""
	def __init__(self, text):
		self.text = text

class STMLParser(NodeVisitor):
	def __init__(self):
		self.current_node = None
		self.root_tags = []

	def visit_doctype(self, _1, _2):
		return None

	def visit_stml_page(self, node, pars):
		(_, _, tags) = pars
		for (_, tag, _) in tags:
			if tag:
				self.root_tags.append(tag)
	
	def visit_attribute(self, node, pars): 
		(name, _, value) = pars
		return {name.text: value.text}
	
	def visit_tag(self, node, children):
		return self.lift_child(node, children)
	
	def visit_tag_open(self, node, pars, self_closing=False):
		(_, _, tagname, _, attributes, _, _) = pars
		html = STMLNode(tagname.text)
		html.self_closing = self_closing
		for (attribute, _) in attributes:
			html.attributes.update(attribute)
		return html

	def visit_tag_self(self, node, pars):
		return self.visit_tag_open(node, pars, self_closing=True)
	
	def visit_tag_body(self, node, children):
		(tag_open, _, inner, _, _) = children
		for child in inner:
			tag_open.children.append(child[0])
		return tag_open

	def visit_ws(self, _1, _2):
		return None
	
	def visit_text(self, node, _):
		return TextNode(node.text)
	
	def generic_visit(self, node, children):
		return children or node


def visit_stml_node(page_root, style, node):
	if not isinstance(node, STMLNode):
		if isinstance(node, TextNode):
			# sub out line breaks for <br>, but only if preceded by an actual character
			return re.sub(r'([^\s])\n', '\\1<br>\n', node.text)
		return node or ''
	tag = stml_rewrite_tag(node)
	if not tag:
		return ''
	if tag == 'head':
		node.children.append('<link rel="stylesheet" href="/static/ds.css">')
		if style:
			node.children.append(style)
	attribs = {}
	css = stml_attrib_css(node)
	if css:
		attribs['style'] = '; '.join(css)
	src = node.attributes.get('source')
	if src:
		attribs['src'] = _rewrite_ds_url(src)
	href = node.attributes.get('to')
	if href:
		href = _rewrite_ds_url(href, page_root)
		if not tag == 'img':
			attribs['href'] = _rewrite_ds_url(href, page_root)
	if 'id' in node.attributes:
		attribs['id'] = '#' + node.attributes.get('id')
	if 'style' in node.attributes:
		attribs['class'] = node.attributes.get('style')
	attrib_text = ' '.join([f'{k}="{v}"' for k, v in attribs.items()])
	if attrib_text:
		attrib_text = ' ' + attrib_text
	html = f'<{tag}{attrib_text}>'
	if tag == 'body':
		# contain the whole stml body in a div root
		html += '<div id="#stml_parser_root">\n'
	if node.self_closing:
		# html can't put hrefs on linked images, wrap in <a>
		if href and tag == 'img':
			return f'<a href="{href}">{html}</a>'
		return html
	for child in node.children:
		html += visit_stml_node(page_root, style, child)
	if tag == 'body':
		html += '</div>\n'
	html += f'</{tag}>'
	return html

def visit_sss_node(node: STMLNode):
	classes = {}
	for style in node.children:
		if not isinstance(style, STMLNode):
			continue
		class_body = '; '.join(stml_attrib_css(style))
		classes[style.attributes['id']] = class_body
	return '<style type="text/css">\n' + '\n'.join([f'.{k} {{ {v} }}' for k, v in classes.items()]) + '</style>'

def stml_rewrite_tag(node: STMLNode):
	return {
		'stml': 'html',
		'text': 'p',
		'link': 'a',
		'block': 'div',
		'rule': 'hr',
		'image': 'img',
		'list': 'ul',
		'item': 'li',
		'soul': None,
		'details': None,
	}.get(node.tag, node.tag)

def stml_attrib_css(node: STMLNode):
	class_attributes = {}
	def _a(key, value):
		class_attributes.update({key: value})
	for k, v in node.attributes.items():
		if k == 'backgroundColor':
			_a('background-color', v)
		elif k == 'textColor':
			_a('color', v)
		elif k == 'width':
			try:
				v = int(v)
				_a('width', f'{v}px')
			except ValueError:
				_a('width', v)
		elif k == 'height':
			try:
				v = int(v)
				_a('height', f'{v}px')
			except ValueError:
				_a('height', v)
		elif k == 'borderColor':
			_a('border-color', v)
			_a('border-style', 'solid')
		elif k == 'borderThickness':
			_a('border-width', f'{v}px')
			_a('border-style', 'solid')
		elif k == 'marginTop':
			_a('margin-top', f'{v}px')
		elif k == 'marginBottom':
			_a('margin-bottom', f'{v}px')
		elif k == 'margin':
			_a('margin', f'{v}px')
		elif k == 'padding':
			_a('padding', f'{v}px')
		elif k == 'align':
			_a('text-align', v)
			_a('align-self', v)
		elif k == 'textSize':
			_a('font-size', f'{v}px')
		elif k == 'backgroundImage':
			_a('background-image', f'url(\'{_rewrite_ds_url(v)}\')')
		elif k == 'fashion':
			_a('font-weight', v)
		elif k == 'display':
			if v == 'floe':
				_a('position', 'absolute')
		elif k == 'x':
			_a('margin-left', f'{v}px !important')
		elif k == 'y':
			_a('margin-top', f'{v}px !important')
		elif k == 'orientation':
			_a('display', 'flex')
			if v == 'horizontal':
				_a('flex-direction', 'row')
			elif v == 'vertical':
				_a('flex-direction', 'column')
	return [f'{k}: {v}' for k, v in class_attributes.items()]

def _rewrite_ds_url(url, page_root=None):
	fs = url.replace('\\', '/')
	if not page_root:
		return f'./{fs.lstrip('/')}'
	return f'{page_root}/{fs}'


def stml_to_html(page_root, document):
	parser = STMLParser()
	parser.grammar = grammar
	parsed = grammar.parse(document)
	parser.visit(parsed)
	html = '<!DOCTYPE html>\n'
	style = ''
	# preprocess certain tags so we can nest them in the html later
	for node in parser.root_tags:
		if node.tag == 'sss':
			style = visit_sss_node(node)
			break
	# find stml tag and parse
	for node in parser.root_tags:
		if node.tag == 'stml':
			html += visit_stml_node(page_root, style, node)
			break
	return html


if __name__ == '__main__':
	# command line usage
	# TODO flags and a way to set page root, but not before href parsing/understanding is fixed
	if len(sys.argv) <= 1:
		print(f'usage: {sys.argv[0]} filename.stml')
		raise SystemExit
	try:
		f = open(sys.argv[1])
	except FileNotFoundError:
		print(f'file not found: {sys.argv[1]}')
	else:
		with f:
			print(stml_to_html('http://localhost:8000/browse', f.read()))