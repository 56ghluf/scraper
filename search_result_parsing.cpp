#include "search_result_parsing.h"
#include "lexbor/dom/interface.h"

#include <iostream>
#include <string>

#include <lexbor/dom/dom.h>
#include <lexbor/html/html.h>

std::ostream &operator<<(std::ostream &ost, const StrAndLen &str) {
  const lxb_char_t *pos{str.cptr};
  for (size_t i{}; i < str.len; ++i, ++pos)
    ost << *pos;

  return ost;
}

lxb_html_document_t *
create_and_parse_document(const std::string &response_text) {
  lxb_html_document_t *document{lxb_html_document_create()};

  if (document == nullptr) {
    std::cerr << "create_and_parse_document: failed to create document\n";

    return nullptr;
  }

  lxb_status_t status{lxb_html_document_parse(
      document, reinterpret_cast<const lxb_char_t *>(response_text.data()),
      response_text.size())};

  if (status != LXB_STATUS_OK) {
    lxb_html_document_destroy(document);
    std::cerr << "create_and_parse_document: failed to parse document\n";
    return nullptr;
  }

  return document;
}

bool col_length_not_one(lxb_dom_collection_t *col, const char *msg) {
  if (lxb_dom_collection_length(col) != 1) {
    std::cerr << msg << '\n';
    lxb_dom_collection_destroy(col, true);
    return true;
  }

  return false;
}

lxb_dom_node_t *retrieve_tinytable(lxb_html_document *document) {
  lxb_dom_collection_t *col{
      lxb_dom_collection_make(&document->dom_document, 1)};

  if (col == nullptr) {
    std::cerr << "retrieve_tinytable: failed to create dom collection\n";
    return nullptr;
  }

  lxb_dom_elements_by_class_name(
      lxb_dom_interface_element(document->body), col,
      reinterpret_cast<const lxb_char_t *>("tinytable"), 9);

  if (col_length_not_one(
          col, "retrieve_tinytable: found more than one tinytable, aborting"))
    return nullptr;

  lxb_dom_node_t *table{lxb_dom_collection_node(col, 0)};
  lxb_dom_collection_destroy(col, true);

  return table;
}

lxb_dom_collection_t *
get_node_children_by_tag_name(lxb_html_document_t *document,
                              lxb_dom_node_t *node, const StrAndLen &tag_name,
                              lxb_dom_collection_t *col, size_t start_size) {
  if (lxb_dom_node_type(node) != LXB_DOM_NODE_TYPE_ELEMENT)
    return nullptr;

  if (col == nullptr) {
    col = lxb_dom_collection_make(&document->dom_document, start_size);

    if (col == nullptr) {
      std::cerr
          << "get_node_children_by_tag_name: failed to create collection\n";
      return nullptr;
    }
  } else
    lxb_dom_collection_clean(col);

  lxb_status_t status{lxb_dom_elements_by_tag_name(
      lxb_dom_interface_element(node), col, tag_name.cptr, tag_name.len)};

  if (status != LXB_STATUS_OK) {
    std::cerr
        << "get_node_children_by_tag_name: failed to find children by tag\n";
    return nullptr;
  }

  return col;
}

StrAndLen get_node_text(lxb_dom_node_t *node) {
  if (node == nullptr)
    return {};

  size_t len;
  lxb_char_t *text{lxb_dom_node_text_content(node, &len)};

  if (text == nullptr)
    return {};

  return {text, len};
}

lexbor_action_t print_text_children_walker(lxb_dom_node_t *node, void *ctx) {
  if (lxb_dom_node_type(node) == LXB_DOM_NODE_TYPE_TEXT) {
    const StrAndLen node_text{get_node_text(node)};

    if (node_text.len != 1 || *node_text.cptr != ' ')
      *static_cast<std::ostream *>(ctx) << get_node_text(node);

    return LEXBOR_ACTION_OK;
  }

  if (lxb_dom_node_tag_id(node) == LXB_TAG_IMAGE) {
    return LEXBOR_ACTION_NEXT;
  }

  if (lxb_dom_node_type(node) == LXB_DOM_NODE_TYPE_ELEMENT)
    return LEXBOR_ACTION_OK;

  return LEXBOR_ACTION_NEXT;
}

void print_col_text_children_by_element(lxb_dom_collection_t *col,
                                        std::ostream &ost) {
  for (size_t i{}; i < lxb_dom_collection_length(col); ++i) {
    lxb_dom_node_simple_walk(lxb_dom_collection_node(col, i),
                             print_text_children_walker, &ost);
    ost << "\x1F";
  }
  ost << "\b\n";
}

void parse_table(const std::string &response_text, std::ostream &ost,
                 bool write_head) {
  lxb_html_document_t *document{create_and_parse_document(response_text)};
  if (document == nullptr)
    return;

  lxb_dom_node_t *table{retrieve_tinytable(document)};
  if (table == nullptr)
    return;

  lxb_dom_collection_t *col{nullptr};

  if (write_head) {
    // Get the table head
    col =
        get_node_children_by_tag_name(document, table, StrAndLen{"thead"}, col);
    if (col == nullptr) {
      std::cerr << "parse_table: failed to get table head, aborting\n";
      return;
    }

    if (col_length_not_one(
            col, "parse_table: found more than one table head, aborting"))
      return;

    lxb_dom_node_t *thead{lxb_dom_collection_node(col, 0)};

    // Get the head's only row
    if (get_node_children_by_tag_name(document, thead, StrAndLen{"tr"}, col) ==
        nullptr) {
      std::cerr << "parse_table: failed to get head's row, aborting\n";
      return;
    }

    if (col_length_not_one(
            col,
            "parse_table: found more than one row in table head, aborting"))
      return;

    lxb_dom_node_t *thead_r{lxb_dom_collection_node(col, 0)};

    // Get all the columns of the first row
    if (get_node_children_by_tag_name(document, thead_r, StrAndLen{"th"},
                                      col) == nullptr) {
      std::cerr << "parse_table: failed to get first rows columns, aborint\n";
      return;
    }

    print_col_text_children_by_element(col, ost);
  }

  // Get table body
  col = get_node_children_by_tag_name(document, table, StrAndLen{"tbody"}, col);
  if (col == nullptr) {
    std::cerr << "parse_table: failed to get table body, aborting\n";
    return;
  }

  if (col_length_not_one(
          col, "parse_table: found more than one table body, aborting"))
    return;

  lxb_dom_node_t *tbody{lxb_dom_collection_node(col, 0)};

  // Get the body's rows
  if (get_node_children_by_tag_name(document, tbody, StrAndLen{"tr"}, col) ==
      nullptr) {
    std::cerr << "parse_table: failed to get body's rows, aborint\n";
    return;
  }

  // In each row, get the column
  for (size_t i{}; i < lxb_dom_collection_length(col); ++i) {
    lxb_dom_collection_t *row_col{get_node_children_by_tag_name(
        document, lxb_dom_collection_node(col, i), StrAndLen("td"))};

    print_col_text_children_by_element(row_col, ost);
  }

  // Clean up, because we are polite
  lxb_dom_collection_destroy(col, true);
  lxb_html_document_destroy(document);
}
