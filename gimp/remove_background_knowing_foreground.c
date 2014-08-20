#include <libgimp/gimp.h>
#include <libgimp/gimpui.h>
static void query (void);
static void run   (const gchar      *name,
                   gint              nparams,
                   const GimpParam  *param,
                   gint             *nreturn_vals,
                   GimpParam       **return_vals);
static void remove_background  (GimpDrawable     *drawable);
static gboolean dialog  (GimpDrawable     *drawable);

GimpPlugInInfo PLUG_IN_INFO =
{
  NULL,
  NULL,
  query,
  run
};

MAIN()

static int radius;

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

  switch (run_mode)
    {
    case GIMP_RUN_INTERACTIVE:
      /* Display the dialog */
      if (! dialog (drawable))
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
  guchar      *row1, *row2, *row3;
  guchar      *outrow;

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

  /* Initialise enough memory for row1, row2, row3, outrow */
  row1 = g_new (guchar, channels * (x2 - x1));
  row2 = g_new (guchar, channels * (x2 - x1));
  row3 = g_new (guchar, channels * (x2 - x1));
  outrow = g_new (guchar, channels * (x2 - x1));

  for (i = y1; i < y2; i++)
    {
      /* Get row i-1, i, i+1 */
      gimp_pixel_rgn_get_row (&rgn_in,
                              row1,
                              x1, MAX (y1, i - 1),
                              x2 - x1);
      gimp_pixel_rgn_get_row (&rgn_in,
                              row2,
                              x1, i,
                              x2 - x1);
      gimp_pixel_rgn_get_row (&rgn_in,
                              row3,
                              x1, MIN (y2 - 1, i + 1),
                              x2 - x1);

      for (j = x1; j < x2; j++)
        {
          /* For each layer, compute the average of the nine
           * pixels */
          for (k = 0; k < channels; k++)
            {
              int sum = 0;
              sum = row1[channels * MAX ((j - 1 - x1), 0) + k]           +
                    row1[channels * (j - x1) + k]                        +
                    row1[channels * MIN ((j + 1 - x1), x2 - x1 - 1) + k] +
                    row2[channels * MAX ((j - 1 - x1), 0) + k]           +
                    row2[channels * (j - x1) + k]                        +
                    row2[channels * MIN ((j + 1 - x1), x2 - x1 - 1) + k] +
                    row3[channels * MAX ((j - 1 - x1), 0) + k]           +
                    row3[channels * (j - x1) + k]                        +
                    row3[channels * MIN ((j + 1 - x1), x2 - x1 - 1) + k];
              outrow[channels * (j - x1) + k] = sum / 9;
            }
        }

      gimp_pixel_rgn_set_row (&rgn_out,
                              outrow,
                              x1, i,
                              x2 - x1);

      if (i % 10 == 0)
        gimp_progress_update ((gdouble) (i - y1) / (gdouble) (y2 - y1));
    }

  g_free (row1);
  g_free (row2);
  g_free (row3);
  g_free (outrow);

  gimp_drawable_flush (drawable);
  gimp_drawable_merge_shadow (drawable->drawable_id, TRUE);
  gimp_drawable_update (drawable->drawable_id,
                        x1, y1,
                        x2 - x1, y2 - y1);
}

static gboolean
dialog (GimpDrawable *drawable)
{
  GtkWidget *dialog;
  GtkWidget *main_vbox;
  GtkWidget *main_hbox;
  GtkWidget *frame;
  GtkWidget *radius_label;
  GtkWidget *alignment;
  GtkWidget *spinbutton;
  GtkObject *spinbutton_adj;
  GtkWidget *frame_label;
  gboolean   run;

  gimp_ui_init ("remove_background", FALSE);

  dialog = gimp_dialog_new ("Remove background", "remove_background",
                            NULL, 0,
                            gimp_standard_help_func, "plug-in-remove-background",

                            GTK_STOCK_CANCEL, GTK_RESPONSE_CANCEL,
                            GTK_STOCK_OK,     GTK_RESPONSE_OK,

                            NULL);

  main_vbox = gtk_vbox_new (FALSE, 6);
  gtk_container_add (GTK_CONTAINER (GTK_DIALOG (dialog)->vbox), main_vbox);
  gtk_widget_show (main_vbox);

  frame = gtk_frame_new (NULL);
  gtk_widget_show (frame);
  gtk_box_pack_start (GTK_BOX (main_vbox), frame, TRUE, TRUE, 0);
  gtk_container_set_border_width (GTK_CONTAINER (frame), 6);

  alignment = gtk_alignment_new (0.5, 0.5, 1, 1);
  gtk_widget_show (alignment);
  gtk_container_add (GTK_CONTAINER (frame), alignment);
  gtk_alignment_set_padding (GTK_ALIGNMENT (alignment), 6, 6, 6, 6);

  main_hbox = gtk_hbox_new (FALSE, 0);
  gtk_widget_show (main_hbox);
  gtk_container_add (GTK_CONTAINER (alignment), main_hbox);

  radius_label = gtk_label_new_with_mnemonic ("_Radius:");
  gtk_widget_show (radius_label);
  gtk_box_pack_start (GTK_BOX (main_hbox), radius_label, FALSE, FALSE, 6);
  gtk_label_set_justify (GTK_LABEL (radius_label), GTK_JUSTIFY_RIGHT);

  spinbutton_adj = gtk_adjustment_new (3, 1, 16, 1, 5, 5);
  spinbutton = gtk_spin_button_new (GTK_ADJUSTMENT (spinbutton_adj), 1, 0);
  gtk_widget_show (spinbutton);
  gtk_box_pack_start (GTK_BOX (main_hbox), spinbutton, FALSE, FALSE, 6);
  gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (spinbutton), TRUE);

  frame_label = gtk_label_new ("<b>Modify radius</b>");
  gtk_widget_show (frame_label);
  gtk_frame_set_label_widget (GTK_FRAME (frame), frame_label);
  gtk_label_set_use_markup (GTK_LABEL (frame_label), TRUE);

  g_signal_connect (spinbutton_adj, "value_changed",
                    G_CALLBACK (gimp_int_adjustment_update),
                    &radius);
  gtk_widget_show (dialog);

  run = (gimp_dialog_run (GIMP_DIALOG (dialog)) == GTK_RESPONSE_OK);

  gtk_widget_destroy (dialog);

  return run;
}
