import numpy as np
from ..geometric_program import GPSolutionArray
from string import Template
import itertools

try:
    from IPython.display import Math, display
except ImportError:
    pass

from widget import widget

def showcadtoon(title, css=None):
    with open("%s.gpkit" % title, 'r') as file:
        display(HTML(file.read()))
        if css: display(HTML("<style> #ractivecontainer { %s } </style>" % css))

def ractorpy(gp, update_py, ranges, constraint_js="", showtables=["cost", "sensitivities"]):
    def ractivefn(gp):
        sol = gp.solution
        live = "<script>" + update_py(sol) + "\n" + constraint_js + "</script>"
        display(HTML(live))
        if showtables:
            print sol.table(showtables)
    return widget(gp, ractivefn, ranges)

new_jswidget_id = itertools.count().next

def ractorjs(title, gp, update_py, ranges, constraint_js=""):
    widget_id = "jswidget_"+str(new_jswidget_id())
    display(HTML("<script id='%s-after' type='text/throwaway'>%s</script>" % (widget_id, constraint_js)))
    display(HTML("<script>var %s = {storage: [], n:%i, ranges: {}, after: document.getElementById('%s-after').innerText, bases: [1] }</script>" % (widget_id, len(ranges), widget_id)))

    container_id = widget_id + "_container"
    display(HTML("<div id='%s'></div><style>#%s td {text-align: right; border: none !important;}\n#%s tr {border: none !important;}\n#%s table {border: none !important;}\n</style>" % (container_id, container_id, container_id, container_id)))

    template_id = widget_id + "_template"
    template = '<script id="%s" type="text/ractive"><table>' % template_id
    ctrl_template = Template('<tr><td>$var</td><input value="{{$varname}}" type="range" min="0" max="$len" step="1"><td><span id="$w-$varname"></span></td></tr>\n')
    data_init = ""

    subs = {}
    lengths = []
    bases = []

    varkeys = gp.unsubbed.varlocs.keys()

    for var, values in ranges.items():
        mini, maxi, step = values
        length = int((maxi-mini)/step) + 1
        lengths.append(length)
        bases.append(np.prod(lengths))
        array = map(lambda x: mini + x*step, range(length))
        if var in varkeys:
            subs[varkeys[varkeys.index(var)]] = ("sweep", array)

    # bug involves things resizing mysteriously when there's >4 vars
    # kinda like swapping wall & floor, but not quite...

    i = 0
    for var, sweepval in subs.items():
        array = sweepval[1]
        varname = "var" + str(i)
        display(HTML("<script>%s.ranges.%s = %s\n%s.bases.push(%i)</script>" % (widget_id, varname, array, widget_id, bases[i])))
        template += ctrl_template.substitute(w=widget_id,
                                             var=("$%s$" % var),
                                             varname=varname,
                                             len=len(array)-1)
        data_init += "%s: %i, " % (varname, (len(array)-1)/2)
        i += 1

    evalarray = [""]*(np.prod(lengths))

    gp.sweep = {}
    gp.prewidget = gp.last
    gp.sub(subs, replace=True)
    sol = gp.solve(printing=False, skipfailures=True)
    for j in range(len(sol)):
        solj = sol.atindex(j)
        soljv = solj["variables"]
        idxs = [subs[var][1].index(soljv[var]) for var in subs]
        k = sum(np.array(idxs) * np.array([1]+bases[:-1]))
        evalarray[k] = update_py(GPSolutionArray(solj))
    display(HTML("<script> %s.storage = %s </script>" % (widget_id, evalarray)))
    gp.load(gp.prewidget, printing=False)

    display(HTML(template + "</table></script>"))

    loader = Template("""getScript('http://cdn.ractivejs.org/latest/ractive.min.js', function() {
          $w.ractive = new Ractive({
          el: '$container_id',
          template: '#$template_id',
          magic: true,
          data: {$data_init},
          onchange: function() {
              var idxsum = 0
              for (var i=0; i<$w.n; i++) {
                  varname = 'var'+i
                  idx = $w.ractive.data[varname]
                  document.getElementById("$w-"+varname).innerText = Math.round(100*$w.ranges[varname][idx])/100
                  idxsum += idx*$w.bases[i]
              }
              if ($w.storage[idxsum] === "") {
                $title.infeasibilitywarning = "Infeasible problem"
              } else {
                $title.infeasibilitywarning = ""
                eval($w.storage[idxsum] + $w.after)
              }
            }
        });

        $w.ractive.onchange()
})</script>""")

    display(HTML("<script>$."+loader.substitute(title=title,
                                                w=widget_id,
                                                container_id=container_id,
                                                template_id=template_id,
                                                data_init=data_init)))
