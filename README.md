#SEPA library

This library allows you to build SEPA XML's using python objects

With this library you can build:

* ISO 20022 - pain.008.001.02 (Direct debit, no B2B)
* ISO 20022 - pain.001.001.03 (Credit transfer)

It depends on [libComXML](https://github.com/gisce/libComXML)

Below you can find a little example on how you should use this library

```python

	from sepa import sepa19

    def _sepa_header(self):
        
        header = sepa19.SepaHeader()
        header_fields = {
            'message_id': message_id,
            'creation_date_time': iso_today,
            'number_of_operations': num_operations,
            'checksum': total,
            'initiating_party': initiating_party
        }
        header.feed(header_fields)
        return header

	def _payments_info(self):
		'''builds payments info'''
		return payments_info

	def build_xml(self):

	    xml = sepa19.DirectDebitInitDocument()
	    direct_debit = sepa19.DirectDebitInitMessage()
	            
	    header = self._sepa_header()
	    payments_info = self._payments_info()
	            
	    direct_debit.feed({
	        'sepa_header': header,
	        'payment_information': payments_info
	    })
	    xml.feed({
	        'customer_direct_debit': direct_debit
	    })
	    
	    xml.pretty_print = True
	    xml.build_tree()
	    return str(xml)
```

## CSV to SEPA XML script
Click script to create a SEPA XML file from CSV data

```
Usage: rebuts.py [OPTIONS]

Options:
  -f, --filepath TEXT      CSV File path. 1 header line.
                           empty;mandate;name;ccc;quantity  [required]
  -c, --config TEXT        config json file with company data  [default:
                           rebuts.json]
  -d, --due-date TEXT      Payment due date  [default: 2023-07-06]
  -n, --payment-name TEXT  SEPA file payment description  [default: SEPA
                           PAYMENT DESCRIPTION]
  -u, --concept TEXT       SEPA file payment description  [default:
                           ORGANIZATION QUOTE]
  -o, --output TEXT        output file_path  [default: /tmp/rebuts.xml]
  --help                   Show this message and exit.
```

* **json config file (-c, --config)**: Sets **static** originating entity data (see rebuts.joson.tmpl)

   * **company_name**: originating partner name `<GrpHdr><InitgPty><Nm>` 

   * **vat**: partner vat

   * **sepa_id**: partner SEPA Identifier `<GrpHdr><InitgPty><Id><OrgId><Othr><Id>`

   * **schmeid**: Partner Scheme Identifier `<PmtInf><CdtrSchmeId><Id><PrvtId><Othr><Id>`

   * **iban**: IBAN number

   * **bic**: Partner bank BIC code

   * **mandate_default_date**: default mandate date

### CSV

CSV file with a line for every debtor line

* Header in first line
* ';'  as delimiter
* first column free (not processed)

```
ROW_POS_MANDATE = 1
ROW_POS_NAME = 2
ROW_POS_IBAN = 3
ROW_POS_AMOUNT = 4
```

**Example:**

```
;MANDATE;NAME;IBAN OR CCC;QUANTITY (€)
;000000001;PUIG PUIG, RAMON;123456789012345;50
;000000002;COSTA COSTA, HELENA;9876543210987;50
``` 
