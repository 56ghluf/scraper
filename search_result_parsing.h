#pragma once

#include <cstring>
#include <ostream>
#include <string>

#include <lexbor/dom/dom.h>
#include <lexbor/html/html.h>

struct StrAndLen {
  const lxb_char_t *cptr;
  size_t len;

  StrAndLen(const lxb_char_t *c = nullptr, size_t l = 0) : cptr{c}, len{l} {}
  StrAndLen(const char *c)
      : StrAndLen{reinterpret_cast<const lxb_char_t *>(c), std::strlen(c)} {}
};

std::ostream &operator<<(std::ostream &, const StrAndLen &);

lxb_html_document_t *create_and_parse_document(const std::string &);

bool col_length_not_one(lxb_dom_collection_t*, const char*);

lxb_dom_node_t *retrieve_tinytable(lxb_html_document *);

// Don't forget to delete the collection once you're done with it
lxb_dom_collection_t *
get_node_children_by_tag_name(lxb_html_document_t *, lxb_dom_node_t *,
                              const StrAndLen &, lxb_dom_collection_t * = nullptr,
                              size_t = 32);

StrAndLen get_node_text(lxb_dom_node_t *);

lexbor_action_t print_text_children_walker(lxb_dom_node_t *, void *);
void print_col_element_text_children(lxb_dom_collection_t *, std::ostream& ost);

void parse_table(const std::string &, std::ostream&, bool);
