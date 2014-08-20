#include <libgimp/gimp.h>
#include <libgimp/gimpui.h>
static void query (void);
static void run   (const gchar      *name,
                   gint              nparams,
                   const GimpParam  *param,
                   gint             *nreturn_vals,
                   GimpParam       **return_vals);
static void remove_background  (GimpDrawable     *drawable);
static gboolean show_dialog  (GimpDrawable     *drawable);

GimpPlugInInfo PLUG_IN_INFO =
{
  NULL,
  NULL,
  query,
  run
};

MAIN()

static GimpRGB backgroundColor;
static GimpRGB foregroundColor;

static void
query (void)
{
  static GimpParamDef args[] =
  {
    {
      GIMP_PDB_INT32,
      "run-mode",
      "Run mode"
    },
    {
      GIMP_PDB_IMAGE,
      "image",
      "Input image"
    },
    {
      GIMP_PDB_DRAWABLE,
      "drawable",
      "Input drawable"
    }
  };

  gimp_install_procedure (
    "plug-in-remove-background",
    "Remove Background",
    "Remove Background",
    "Martin Bonnin",
    "Copyright Martin Bonnin",
    "2014",
    "_Remove Background",
    "RGB*, GRAY*",
    GIMP_PLUGIN,
    G_N_ELEMENTS (args), 0,
    args, NULL);

  gimp_plugin_menu_register ("plug-in-remove-background",
                             "<Image>/Colors/Auto");
}

static void
run (const gchar      *name,
     gint              nparams,
     const GimpParam  *param,
     gint             *nreturn_vals,
     GimpParam       **return_vals)
{
  static GimpParam  values[1];
  GimpPDBStatusType status = GIMP_PDB_SUCCESS;
  GimpRunMode       run_mode;
  GimpDrawable     *drawable;

  /* Setting mandatory output values */
  *nreturn_vals = 1;
  *return_vals  = values;

  values[0].type = GIMP_PDB_STATUS;
  values[0].data.d_status = status;

  /* Getting run_mode - we won't display a dialog if
   * we are in NONINTERACTIVE mode
   */
  run_mode = param[0].data.d_int32;

  /*  Get the specified drawable  */
  drawable = gimp_drawable_get (param[2].data.d_drawable);

  if (!gimp_drawable_has_alpha (drawable->drawable_id)) {
	g_message("You need an alpha channel");
    return;
  }
  
  switch (run_mode)
    {
    case GIMP_RUN_INTERACTIVE:
      /* Display the dialog */
      if (! show_dialog (drawable))
        return;
      break;

    case GIMP_RUN_NONINTERACTIVE:
      if (nparams != 4)
        status = GIMP_PDB_CALLING_ERROR;
      break;

    case GIMP_RUN_WITH_LAST_VALS:
      break;

    default:
      break;
    }

  gimp_progress_init ("Remove Background...");

  /* Let's time blur
   *
   *   GTimer timer = g_timer_new time ();
   */

  remove_background (drawable);

  /*   g_print ("blur() took %g seconds.\n", g_timer_elapsed (timer));
   *   g_timer_destroy (timer);
   */

  gimp_displays_flush ();
  gimp_drawable_detach (drawable);

  return;
}

static void
remove_background (GimpDrawable *drawable)
{
  gint         i, j, k, channels;
  gint         x1, y1, x2, y2;
  GimpPixelRgn rgn_in, rgn_out;
  guchar      *row;
  guchar      *outrow;
  GimpRGB bc = backgroundColor;
  GimpRGB fc = foregroundColor;
  
  bc.r *= 255;
  bc.g *= 255;
  bc.b *= 255;
  fc.r *= 255;
  fc.g *= 255;
  fc.b *= 255;

  gimp_drawable_mask_bounds (drawable->drawable_id,
                             &x1, &y1,
                             &x2, &y2);
  channels = gimp_drawable_bpp (drawable->drawable_id);

  gimp_pixel_rgn_init (&rgn_in,
                       drawable,
                       x1, y1,
                       x2 - x1, y2 - y1,
                       FALSE, FALSE);
  gimp_pixel_rgn_init (&rgn_out,
                       drawable,
                       x1, y1,
                       x2 - x1, y2 - y1,
                       TRUE, TRUE);

  row = g_new (guchar, channels * (x2 - x1));
  outrow = g_new (guchar, channels * (x2 - x1));

  for (i = y1; i < y2; i++)
    {
      gimp_pixel_rgn_get_row (&rgn_in,
                              row,
                              x1, i,
                              x2 - x1);

      for (j = x1; j < x2; j++)
        {
          int alpha;
          
          guchar *in = &row[channels * (j - x1)];
          guchar *out = &outrow[channels * (j - x1)];
          
          double den = (fc.r - bc.r) * (fc.r - bc.r) + (fc.g - bc.g) * (fc.g - bc.g) + (fc.b - bc.b) * (fc.b - bc.b);
          double num = (fc.r - bc.r) * (in[0] - bc.r) + (fc.g - bc.g) * (in[1] - bc.g) + (fc.b - bc.b) * (in[2] - bc.b);
          
          alpha = 255 * num / den;
		  if (alpha < 0) {
			  alpha = 0;
		  } else if (alpha > 255) {
			  alpha = 255;
		  }
		  out[0] = 255 * fc.r;
		  out[1] = 255 * fc.g;
		  out[2] = 255 * fc.b;
		  out[3] = alpha;
        }

      gimp_pixel_rgn_set_row (&rgn_out,
                              outrow,
                              x1, i,
                              x2 - x1);

      if (i % 10 == 0)
        gimp_progress_update ((gdouble) (i - y1) / (gdouble) (y2 - y1));
    }

  g_free (row);
  g_free (outrow);

  gimp_drawable_flush (drawable);
  gimp_drawable_merge_shadow (drawable->drawable_id, TRUE);
  gimp_drawable_update (drawable->drawable_id,
                        x1, y1,
                        x2 - x1, y2 - y1);
}

static gboolean
show_dialog (GimpDrawable *drawable)
{
  GtkWidget *dialog;
  GtkWidget *vbox;
  GtkWidget *hbox;
  GtkWidget *label;
  GtkWidget *foregroundButton;
  GtkWidget *backgroundButton;
  gboolean   run;

  gimp_ui_init ("remove_background", FALSE);

  dialog = gimp_dialog_new ("Remove background", "remove_background",
                            NULL, 0,
                            gimp_standard_help_func, "plug-in-remove-background",

                            GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
                            GTK_STOCK_OK,     GTK_RESPONSE_OK,

                            NULL);

  vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_add (GTK_CONTAINER (GTK_DIALOG (dialog)->vbox), vbox);
  gtk_widget_show (vbox);
  
  hbox = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_container_add (GTK_CONTAINER (vbox), hbox);
  gtk_widget_show(hbox);
  
  label = gtk_label_new_with_mnemonic ("Background:");
  gtk_container_add (GTK_CONTAINER (hbox), label);
  gtk_widget_show (label);
  
  backgroundButton = gimp_color_button_new("Background color", 32, 32, &backgroundColor, GIMP_COLOR_AREA_FLAT);
  g_signal_connect (backgroundButton, "color-changed",
                    G_CALLBACK (gimp_color_button_get_color),
                    &backgroundColor);
  gtk_container_add (GTK_CONTAINER (hbox), backgroundButton);
  gtk_widget_show (backgroundButton);
  
  hbox = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_container_add (GTK_CONTAINER (vbox), hbox);
  gtk_widget_show(hbox);
  
  label = gtk_label_new_with_mnemonic ("Foreground:");
  gtk_container_add (GTK_CONTAINER (hbox), label);
  gtk_widget_show (label);
  
  foregroundButton = gimp_color_button_new("Foreground color", 32, 32, &foregroundColor, GIMP_COLOR_AREA_FLAT);
  g_signal_connect (foregroundButton, "color-changed",
                    G_CALLBACK (gimp_color_button_get_color),
                    &foregroundColor);
  gtk_container_add (GTK_CONTAINER (hbox), foregroundButton);
  gtk_widget_show (foregroundButton);

  gtk_widget_show (dialog);

  run = (gimp_dialog_run (GIMP_DIALOG (dialog)) == GTK_RESPONSE_OK);

  gimp_color_button_get_color((GimpColorButton*)foregroundButton, &foregroundColor);
  gimp_color_button_get_color((GimpColorButton*)backgroundButton, &backgroundColor);
  
  gtk_widget_destroy (dialog);

  return run;
}
