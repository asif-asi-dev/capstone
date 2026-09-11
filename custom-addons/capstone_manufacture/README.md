# Capstone Manufacture (Odoo 17)

Community-compatible employee access restrictions, optional BoM manufacturing
output destinations, and hourly/piece/batch processing costs. Depends on Employees
and the standard Manufacturing Accounting integration (`mrp_account`, including
Manufacturing and Inventory Accounting); no Enterprise module is required. This
does not provide the Enterprise Shop Floor application.

## Installation

The repository's `odoo.conf` already includes `capstone/custom-addons` in its addons
path. Restart Odoo, update the Apps list, remove the Apps filter if necessary, and
install **Capstone Manufacture**. Install first in a test database.

## Employee access

1. Give each operator an individual internal Odoo login with Manufacturing / User
   access. Link that login on the employee record (HR can configure the link).
2. As a Manufacturing Administrator, open Manufacturing > Configuration > Work
   Centers > General Information > Employee Access.
3. Select the **Allowed Employees** for each center. Populate these lists before
   operators resume work: an empty list means administrators only.
4. Operators can search, open, and operate only assigned centers and work orders.
   Their work-center time logs are restricted too. These are server-side global
   record rules, not just menu filters. Existing company rules still apply.

Manufacturing Administrators and Odoo superuser operations bypass the assignment
restriction. Do not make an operator a Manufacturing Administrator. Archiving an
employee or changing the linked user updates access. The assignment controls who
can work at a center; it does not assign one exclusive owner to an individual WO.

This is not an inventory, BoM, MO, or accounting confidentiality system: those
models retain standard access. Plan and confirm production as a manager. MOs with
multiple centers can require manager handling because an operator cannot access
another center's WOs; the intended workflow is one stage/center per MO.

Custom fields use a `capstone_` prefix to avoid colliding with Enterprise fields.
If Enterprise is later installed, its Allowed Employees setting remains separate.

## Finished product destinations

1. Create an internal location, e.g. WH/Stock/Finished Goods, in the desired
   warehouse and company.
2. Open the final product BoM > Miscellaneous > Finished Product Destination.
3. Enable **Produce to a Different Location** (disabled by default).
4. Choose a **Manufacturing Operation Type** belonging to the intended warehouse.
5. Choose **Finished Products Location**. The selector includes only active
   internal locations below that warehouse. Server-side validation also checks it.

New MOs default their Finished Products Location from this BoM. Component source
locations follow normal Odoo behavior. Finished stock moves, including by-products,
follow the MO destination. An explicit MO destination is still permitted, just as
in standard Odoo. A later BoM configuration edit does not redirect existing MOs;
review/reselect the BoM on a draft MO or adjust its destination deliberately.

Use separate BoMs for Cast Body, Ground Body, Threaded Body, and Finished Tap.
Enable the override only on the final stage if intermediate outputs should remain
in normal stock. This module does not create those products, BoMs, or orders.

## Default manufacturing-order grouping

Manufacturing > Operations > Manufacturing Orders opens grouped by **Product**,
using Odoo's existing Group By > Product filter. The standard To Do filter and
default company are retained. Users can remove the grouping from the search bar;
a saved default favorite may override these defaults. Upgrade the module after
adding this feature to an already-installed database.

## Piece and batch processing costs

After upgrading the module, open a BoM > Operations > an operation > Processing
Cost. Choose:

| Method | Rate and actual charge |
| --- | --- |
| Hourly (default) | Standard Odoo work-center hourly rate and tracked time. |
| Per Piece | Piece rate times chargeable quantity, in the finished product's inventory UoM. |
| Fixed per Batch | One fixed rate per work order if Apply Batch Charge is enabled. |

For Per Piece choose either **Processed Pieces (Including Rejects)** or **Good
Output Only**. The former requires the operator to enter Processed Chargeable
Quantity and tick Charge Confirmed on the work order. The latter uses actual MO
output, converted to the product's inventory UoM. For example, at 12 per piece,
10 processed and 8 good means a charge of 120 on the processed basis or 96 on the
good basis. Zero is permitted only as an explicit confirmed processed charge.

For Fixed per Batch, a new work order starts with Apply Batch Charge enabled.
Confirm the decision before finishing. One work order with 8 or 25 pieces has the
same fixed fee; this is not a capacity-based fee per N pieces. Manufacturing
Administrators can waive the charge, then reconfirm it. Operators can confirm
quantities and charges but cannot change methods, rates, bases, or the batch flag.

Method, rate, and basis are copied to each new work order. Editing the operation
later does not change that order's saved rates. An administrator can adjust rates
on an open MO; charges cannot be edited after the MO is done or cancelled. Existing
work orders retain Hourly after upgrade; select custom settings deliberately on
those orders if needed. Scheduling and recorded times continue to work normally.

### Splits, backorders, and duplicates

Copied work orders (including split/backorder children) retain their saved rates
but start with zero processed quantity, Charge Confirmed off, and Apply Batch
Charge off. This prevents copying the original fixed fee automatically. Before
finishing a child batch work order, a manager must decide whether to enable a new
fee or leave it waived; confirm the result. The original retains its charge. For
piece costing, enter only that order's chargeable processed quantity; the module
does not infer how processed rejects should be divided among split orders.

### Cost estimates, reports, and inventory value

Custom charges replace hourly processing cost in the BoM estimate, Compute Price
from BoM, MO overview (open and completed), actual manufacturing valuation, and
work-order analytic amounts. Hourly methods remain standard. Analytics retain
working hours as their quantity/UoM; their monetary amount uses the chosen method.

For a batch estimate, the BoM quantity is the costing batch size. Example: a BoM
for 10 units with a fixed operation fee of 150 contributes 15 per unit to Compute
Price from BoM. A one-unit BoM contributes 150 per unit. On the actual MO, the fee
is still 150 once, divided among the actual good output. Enter a realistic BoM
batch quantity if using its unit-cost estimate. Piece estimates use planned output
and do not predict rejects; actual processed quantities can exceed good output.

AVCO/FIFO finished products include these charges in their incoming valuation;
Standard Price still values finished stock at its configured standard. Existing
by-product cost shares apply to the combined material and processing cost. These
features do not implement payroll, employee-specific rates, vendor payments, or
separate accounting for abnormal loss.

### Standard alternative and warehouse routes

Odoo's manufacturing operation type already has source and destination defaults.
For an entire production line sharing the same output location, a dedicated
manufacturing operation type with that destination can avoid a BoM override.

This feature changes the MO output destination directly; it does not create a
separate transfer or rewrite chained procurement/putaway routes. For three-step
manufacturing, use the warehouse's finished-product transfer to move from
post-production to storage, or configure its routing deliberately. Review chained
delivery/replenishment flows when producing outside their expected source location.

## Verification

Tests in `tests/test_manufacture.py` exercise record access, employee changes,
invalid warehouse locations, default/overridden destinations, and completion into
the configured stock location. Run with an isolated database:

```sh
python odoo-bin --addons-path=addons,capstone/custom-addons -d TEST_DATABASE \
  -i capstone_manufacture --test-enable --test-tags /capstone_manufacture \
  --stop-after-init --without-demo=all --http-port=18069
```
